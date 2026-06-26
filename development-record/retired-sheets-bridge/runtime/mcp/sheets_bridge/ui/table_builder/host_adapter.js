(function installSheetsBridgeHostAdapters(global) {
  function parseMessage(raw) {
    if (typeof raw === "string") {
      try {
        return JSON.parse(raw);
      } catch (_error) {
        return null;
      }
    }
    return raw && typeof raw === "object" ? raw : null;
  }

  function createMcpAppsHostAdapter(options) {
    const config = options || {};
    const targetWindow = config.targetWindow || global.parent || global;
    const addMessageListener = config.addMessageListener || function addMessageListener(handler) {
      global.addEventListener("message", handler);
    };
    const postMessage = config.postMessage || function postMessage(message) {
      targetWindow.postMessage(message, "*");
    };
    const setStatus = config.setStatus || function noop() {};
    const timeoutMs = Number(config.timeoutMs || 30000);
    const appInfo = config.appInfo || {
      name: "sheets-bridge-table-builder",
      title: "Spreadsheet Table Builder",
      version: "1.0.0",
      description: "Sketch a desired spreadsheet output table and submit it as a TableBuildIntent."
    };
    let rpcId = 1;
    const pending = new Map();
    const toolInputHandlers = [];
    const toolResultHandlers = [];

    function rpc(method, params) {
      return new Promise((resolve, reject) => {
        const id = `app-${rpcId++}`;
        postMessage({ jsonrpc: "2.0", id, method, params: params || {} });
        const timer = global.setTimeout || setTimeout;
        const timerId = timer(() => {
          if (pending.has(id)) {
            pending.delete(id);
            reject(new Error(`${method} timed out`));
          }
        }, timeoutMs);
        pending.set(id, { resolve, reject, timerId });
      });
    }

    function notify(method, params) {
      postMessage({ jsonrpc: "2.0", method, params: params || {} });
    }

    addMessageListener((event) => {
      const msg = parseMessage(event.data);
      if (!msg || msg.jsonrpc !== "2.0") {
        return;
      }
      if (msg.id && pending.has(msg.id)) {
        const entry = pending.get(msg.id);
        pending.delete(msg.id);
        const clearTimer = global.clearTimeout || clearTimeout;
        clearTimer(entry.timerId);
        if (msg.error) {
          entry.reject(new Error(msg.error.message || "RPC error"));
        } else {
          entry.resolve(msg.result);
        }
        return;
      }
      if (msg.method === "ui/notifications/tool-result") {
        const params = msg.params || {};
        const content = params.structuredContent || (params.result && params.result.structuredContent) || params;
        toolResultHandlers.forEach((handler) => handler(content));
      }
      if (msg.method === "ui/notifications/tool-input") {
        toolInputHandlers.forEach((handler) => handler(msg.params || {}));
      }
      if (msg.method === "ui/resource-teardown" && msg.id) {
        postMessage({ jsonrpc: "2.0", id: msg.id, result: {} });
      }
    });

    return {
      initialize: async function initialize() {
        try {
          await rpc("ui/initialize", {
            protocolVersion: "2026-01-26",
            appInfo,
            appCapabilities: { availableDisplayModes: ["inline", "fullscreen"] }
          });
        } catch (_error) {
          setStatus("MCP Apps bridge 응답을 기다리는 중입니다. tool 결과가 도착하면 화면이 열립니다.");
        }
        notify("ui/notifications/initialized", {});
      },
      onToolInput: function onToolInput(callback) {
        toolInputHandlers.push(callback);
      },
      onToolResult: function onToolResult(callback) {
        toolResultHandlers.push(callback);
      },
      callTool: function callTool(name, args) {
        return rpc("tools/call", { name, arguments: args || {} });
      },
      updateModelContext: function updateModelContext(payload) {
        return rpc("ui/update-model-context", payload || {});
      },
      sendMessage: function sendMessage(text) {
        return rpc("ui/message", {
          role: "user",
          content: [{ type: "text", text: String(text || "") }]
        });
      },
      reportError: function reportError(error) {
        const message = error && error.message ? error.message : String(error || "Unknown host adapter error");
        setStatus(`호스트 연결 오류: ${message}`);
      }
    };
  }

  function createStandaloneHostAdapter(options) {
    const config = options || {};
    const setStatus = config.setStatus || function noop() {};
    const tools = config.tools || {};
    const sentMessages = [];
    const modelContextUpdates = [];
    const toolInputHandlers = [];
    const toolResultHandlers = [];
    return {
      sentMessages,
      modelContextUpdates,
      initialize: async function initialize() {
        setStatus("로컬 테스트 모드입니다. MCP host 없이 화면 동작만 확인합니다.");
      },
      onToolInput: function onToolInput(callback) {
        toolInputHandlers.push(callback);
      },
      onToolResult: function onToolResult(callback) {
        toolResultHandlers.push(callback);
      },
      callTool: async function callTool(name, args) {
        if (!tools[name]) {
          const error = new Error(`standalone tool is not configured: ${name}`);
          setStatus(error.message);
          throw error;
        }
        return tools[name](args || {});
      },
      updateModelContext: async function updateModelContext(payload) {
        modelContextUpdates.push(payload || {});
        return {};
      },
      sendMessage: async function sendMessage(text) {
        sentMessages.push(String(text || ""));
        return {};
      },
      reportError: function reportError(error) {
        const message = error && error.message ? error.message : String(error || "Unknown host adapter error");
        setStatus(`로컬 테스트 오류: ${message}`);
      },
      emitToolInput: function emitToolInput(payload) {
        toolInputHandlers.forEach((handler) => handler(payload || {}));
      },
      emitToolResult: function emitToolResult(payload) {
        toolResultHandlers.forEach((handler) => handler(payload || {}));
      }
    };
  }

  global.SheetsBridgeHostAdapters = {
    createMcpAppsHostAdapter,
    createStandaloneHostAdapter
  };
})(typeof globalThis !== "undefined" ? globalThis : window);

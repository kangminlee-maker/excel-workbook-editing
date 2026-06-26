from __future__ import annotations

import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node is required for table-builder host adapter JS tests")
class TableBuilderHostAdapterJsTest(unittest.TestCase):
    def test_mcp_apps_adapter_translates_post_message_rpc(self) -> None:
        script = _node_script(r"""
const messages = [];
const listeners = {};
const statuses = [];
const context = {
  console,
  setTimeout,
  clearTimeout,
  parent: { postMessage: message => messages.push(message) },
  addEventListener: (type, handler) => { listeners[type] = handler; }
};
context.globalThis = context;
vm.runInNewContext(adapterSource, context);
const adapter = context.SheetsBridgeHostAdapters.createMcpAppsHostAdapter({
  setStatus: text => statuses.push(text),
  timeoutMs: 1000
});
const toolResults = [];
adapter.onToolResult(content => toolResults.push(content));
const init = adapter.initialize();
const initMessage = messages.find(item => item.method === 'ui/initialize');
assert(initMessage, 'initialize RPC was sent');
listeners.message({ data: { jsonrpc: '2.0', id: initMessage.id, result: {} } });
await init;
assert(messages.some(item => item.method === 'ui/notifications/initialized'), 'initialized notification was sent');
listeners.message({
  data: {
    jsonrpc: '2.0',
    method: 'ui/notifications/tool-result',
    params: { structuredContent: { app_source: { source: { qualified_range: "'Raw'!A1:C4" } } } }
  }
});
assert.equal(toolResults.length, 1);
const call = adapter.callTool('spreadsheet_table_builder_save_intent', { intent: { output_canvas: [['x']], llm_prompt: '요청' } });
const toolCall = messages.find(item => item.method === 'tools/call');
assert(toolCall, 'tools/call RPC was sent');
assert.equal(toolCall.params.name, 'spreadsheet_table_builder_save_intent');
listeners.message({
  data: {
    jsonrpc: '2.0',
    id: toolCall.id,
    result: { structuredContent: { intent_id: 'intent-1', next_prompt: 'plan please' } }
  }
});
const callResult = await call;
assert.equal(callResult.structuredContent.intent_id, 'intent-1');
await adapter.updateModelContext({ structuredContent: { ok: true } }).catch(() => {});
await adapter.sendMessage('plan please').catch(() => {});
assert(messages.some(item => item.method === 'ui/update-model-context'), 'model context update was sent');
assert(messages.some(item => item.method === 'ui/message'), 'ui/message was sent');
console.log('mcp apps adapter ok');
""")
        completed = subprocess.run(
            [NODE, "-e", script],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("mcp apps adapter ok", completed.stdout)

    def test_standalone_adapter_reports_missing_tool_without_side_effect(self) -> None:
        script = _node_script(r"""
const statuses = [];
const context = { console, setTimeout, clearTimeout };
context.globalThis = context;
vm.runInNewContext(adapterSource, context);
const adapter = context.SheetsBridgeHostAdapters.createStandaloneHostAdapter({
  setStatus: text => statuses.push(text)
});
await adapter.initialize();
let rejected = false;
try {
  await adapter.callTool('spreadsheet_table_builder_save_intent', {});
} catch (error) {
  rejected = true;
  assert(error.message.includes('standalone tool is not configured'));
}
assert(rejected, 'missing standalone tool should reject');
assert(statuses.some(text => text.includes('로컬 테스트 모드입니다')));
assert(statuses.some(text => text.includes('standalone tool is not configured')));
await adapter.updateModelContext({ structuredContent: { ok: true } });
await adapter.sendMessage('next prompt');
assert.equal(adapter.modelContextUpdates.length, 1);
assert.equal(adapter.sentMessages[0], 'next prompt');
console.log('standalone adapter ok');
""")
        completed = subprocess.run(
            [NODE, "-e", script],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("standalone adapter ok", completed.stdout)


def _node_script(body: str) -> str:
    return (
        textwrap.dedent(
            """
            const fs = require('fs');
            const vm = require('vm');
            const assert = require('assert');
            const adapterSource = fs.readFileSync('mcp/sheets_bridge/ui/table_builder/host_adapter.js', 'utf8');

            (async () => {
            """
        )
        + body
        + textwrap.dedent(
            """
            })().catch(error => {
              console.error(error);
              process.exit(1);
            });
            """
        )
    )


if __name__ == "__main__":
    unittest.main()

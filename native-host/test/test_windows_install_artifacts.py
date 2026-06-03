from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WindowsInstallArtifactTests(unittest.TestCase):
    def test_windows_wrapper_prefers_python_launcher_and_preserves_exit_code(self) -> None:
        wrapper = (ROOT / "bin" / "sheets-bridge-native-host.cmd").read_text()

        self.assertIn("where py", wrapper)
        self.assertIn('py -3 "%SCRIPT_DIR%sheets-bridge-native-host"', wrapper)
        self.assertIn('python "%SCRIPT_DIR%sheets-bridge-native-host"', wrapper)
        self.assertIn("exit /b %ERRORLEVEL%", wrapper)

    def test_windows_installer_registers_chrome_native_host_for_current_user(self) -> None:
        installer = (ROOT / "install_windows.ps1").read_text()

        self.assertIn("com.day1company.sheets_bridge", installer)
        self.assertIn("chrome-extension://jahlkdjaokmjbipfhlhnjggcgjmpeiij/", installer)
        self.assertIn("HKCU:\\Software\\Google\\Chrome\\NativeMessagingHosts", installer)
        self.assertIn("ConvertTo-Json", installer)
        self.assertIn("Set-Item -Path $RegistryPath -Value $ManifestPath", installer)
        self.assertIn("sheets-bridge-native-host.cmd", installer)


if __name__ == "__main__":
    unittest.main()

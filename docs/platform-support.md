# Platform Support

1. **Development Mode**: Windows (or macOS). The API and frontend can run locally for UI/UX testing and pipeline testing. OS operations like `psutil` may work, but system actions return `UNSUPPORTED_PLATFORM`.
2. **Runtime Mode**: Ubuntu 24.04 LTS. This is the production target. All filesystem operations and bash verifications execute properly here.

To check platform support programmatically, `app.adapters.linux.system.info.runtime_platform` differentiates `WINDOWS_DEVELOPMENT` and `LINUX_RUNTIME`.

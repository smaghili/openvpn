# OpenVPN Dual Auth Installer

A minimal, production-grade OpenVPN installer with dual authentication (certificate + username/password) for Ubuntu 18+.

---

### Recommended Installation (Python-based)

This method uses the new, refactored Python application for a more robust and maintainable installation. It is the recommended way to set up your VPN server.

```bash
bash <(curl -Ls https://raw.githubusercontent.com/smaghili/openvpn/main/deploy.sh)
```

### Legacy Installation (Shell-based)

This is the original shell-based installer. It is still functional but no longer under active development.

```bash
bash <(curl -Ls https://raw.githubusercontent.com/smaghili/openvpn/main/install.sh)
```

---

- **Main idea inspired by:** [angristan/openvpn-install](https://github.com/angristan/openvpn-install)
- **Supported OS:** Ubuntu 18.04 and newer
- **Key Features:**
  - Simple, clean, and professional
  - Dual authentication: each user gets both certificate and login access
  - Robust backup and restore functionality
  - Designed for maintainability and real-world production use

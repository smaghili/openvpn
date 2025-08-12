# OpenVPN Manager with UDS Traffic Monitoring

A comprehensive OpenVPN management system with **near real-time traffic monitoring** using Unix Domain Sockets (UDS), dual authentication, and production-grade monitoring capabilities.

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

### API Secret Key

Before starting the API server, set a secret key via the `API_SECRET_KEY` environment variable:

```bash
export API_SECRET_KEY="your-strong-secret-key"
```

The application will fail to start if this variable is missing.

---

- **Main idea inspired by:** [angristan/openvpn-install](https://github.com/angristan/openvpn-install)
- **Supported OS:** Ubuntu 18.04 and newer
- **Key Features:**
  - **Near real-time traffic monitoring** (5-10 second updates via UDS)
  - **Accurate quota enforcement** with buffer-based cutoff
  - **Zero network exposure** (UDS-based communication, no TCP ports)
  - Dual authentication: each user gets both certificate and login access
  - **Production-ready monitoring** with systemd service and log rotation
  - Robust backup and restore functionality
  - Designed for maintainability and real-world production use
  - **Complete TCP monitor removal** - old 7505/7506 ports eliminated

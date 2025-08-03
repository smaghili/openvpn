#!/bin/bash
# shellcheck disable=SC1091,SC2164,SC2034,SC1072,SC1073,SC1009

# Secure OpenVPN server installer for Debian, Ubuntu, CentOS, Amazon Linux 2, Fedora, Oracle Linux 8, Arch Linux, Rocky Linux and AlmaLinux.
# https://github.com/angristan/openvpn-install

function isRoot() {
	if [ "$EUID" -ne 0 ]; then
		return 1
	fi
}

function tunAvailable() {
	if [ ! -e /dev/net/tun ]; then
		return 1
	fi
}

function checkOS() {
	if [[ -e /etc/debian_version ]]; then
		source /etc/os-release
		if [[ $ID == "ubuntu" ]]; then
			OS="ubuntu"
			MAJOR_UBUNTU_VERSION=$(echo "$VERSION_ID" | cut -d '.' -f1)
			if [[ $MAJOR_UBUNTU_VERSION -lt 18 ]]; then
				echo "⚠️ Your version of Ubuntu is not supported."
				echo ""
				echo "This script only supports Ubuntu 18.04 and newer versions."
				echo ""
				exit 1
			fi
		else
			echo "⚠️ This script only supports Ubuntu 18.04 and newer."
			echo "Your system appears to be: $ID"
			exit 1
		fi
	else
		echo "⚠️ This script only supports Ubuntu 18.04 and newer."
		echo "Please run this script on an Ubuntu system."
		exit 1
	fi
}

function initialCheck() {
	if ! isRoot; then
		echo "Sorry, you need to run this script as root."
		exit 1
	fi
	if ! tunAvailable; then
		echo "TUN is not available."
		exit 1
	fi
	checkOS
}

function installUnbound() {
	# If Unbound isn't installed, install it
	if [[ ! -e /etc/unbound/unbound.conf ]]; then
		apt-get install -y unbound

		# Configuration for Ubuntu
		echo 'interface: 10.8.0.1
access-control: 10.8.0.1/24 allow
hide-identity: yes
hide-version: yes
use-caps-for-id: yes
prefetch: yes' >>/etc/unbound/unbound.conf

		# IPv6 DNS support
		if [[ $IPV6_SUPPORT == 'y' ]]; then
			echo 'interface: fd42:42:42:42::1
access-control: fd42:42:42:42::/112 allow' >>/etc/unbound/unbound.conf
		fi

		# DNS Rebinding fix
		echo "private-address: 10.0.0.0/8
private-address: fd42:42:42:42::/112
private-address: 172.16.0.0/12
private-address: 192.168.0.0/16
private-address: 169.254.0.0/16
private-address: fd00::/8
private-address: fe80::/10
private-address: 127.0.0.0/8
private-address: ::ffff:0:0/96" >>/etc/unbound/unbound.conf
		
	else # Unbound is already installed
		echo 'include: /etc/unbound/openvpn.conf' >>/etc/unbound/unbound.conf

		# Add Unbound 'server' for the OpenVPN subnet
		echo 'server:
interface: 10.8.0.1
access-control: 10.8.0.1/24 allow
hide-identity: yes
hide-version: yes
use-caps-for-id: yes
prefetch: yes
private-address: 10.0.0.0/8
private-address: fd42:42:42:42::/112
private-address: 172.16.0.0/12
private-address: 192.168.0.0/16
private-address: 169.254.0.0/16
private-address: fd00::/8
private-address: fe80::/10
private-address: 127.0.0.0/8
private-address: ::ffff:0:0/96' >/etc/unbound/openvpn.conf
		if [[ $IPV6_SUPPORT == 'y' ]]; then
			echo 'interface: fd42:42:42:42::1
access-control: fd42:42:42:42::/112 allow' >>/etc/unbound/openvpn.conf
		fi
	fi

	systemctl enable unbound
	systemctl restart unbound
}

function resolvePublicIP() {
	# IP version flags, we'll use as default the IPv4
	CURL_IP_VERSION_FLAG="-4"
	DIG_IP_VERSION_FLAG="-4"

	# Behind NAT, we'll default to the publicly reachable IPv4/IPv6.
	if [[ $IPV6_SUPPORT == "y" ]]; then
		CURL_IP_VERSION_FLAG=""
		DIG_IP_VERSION_FLAG="-6"
	fi

	# If there is no public ip yet, we'll try to solve it using: https://api.seeip.org
	if [[ -z $PUBLIC_IP ]]; then
		PUBLIC_IP=$(curl -f -m 5 -sS --retry 2 --retry-connrefused "$CURL_IP_VERSION_FLAG" https://api.seeip.org 2>/dev/null)
	fi

	# If there is no public ip yet, we'll try to solve it using: https://ifconfig.me
	if [[ -z $PUBLIC_IP ]]; then
		PUBLIC_IP=$(curl -f -m 5 -sS --retry 2 --retry-connrefused "$CURL_IP_VERSION_FLAG" https://ifconfig.me 2>/dev/null)
	fi

	# If there is no public ip yet, we'll try to solve it using: https://api.ipify.org
	if [[ -z $PUBLIC_IP ]]; then
		PUBLIC_IP=$(curl -f -m 5 -sS --retry 2 --retry-connrefused "$CURL_IP_VERSION_FLAG" https://api.ipify.org 2>/dev/null)
	fi

	# If there is no public ip yet, we'll try to solve it using: ns1.google.com
	if [[ -z $PUBLIC_IP ]]; then
		PUBLIC_IP=$(dig $DIG_IP_VERSION_FLAG TXT +short o-o.myaddr.l.google.com @ns1.google.com | tr -d '"')
	fi

	if [[ -z $PUBLIC_IP ]]; then
		echo >&2 echo "Couldn't solve the public IP"
		exit 1
	fi

	echo "$PUBLIC_IP"
}

function installQuestions() {
	echo "OpenVPN Dual Auth Installer"
	echo "Repository: https://github.com/smaghili/openvpn"
	echo ""
	IP=$(hostname -I | awk '{print $1}')
	read -rp "Server IP address: " -e -i "$IP" IP
	if echo "$IP" | grep -qE '^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168)'; then
		read -rp "Public IP or hostname (NAT): " -e ENDPOINT
	fi

	echo ""
	echo "Checking for IPv6 connectivity..."
	echo ""
	# "ping6" and "ping -6" availability varies depending on the distribution
	if type ping6 >/dev/null 2>&1; then
		PING6="ping6 -c3 ipv6.google.com > /dev/null 2>&1"
	else
		PING6="ping -6 -c3 ipv6.google.com > /dev/null 2>&1"
	fi
	if eval "$PING6"; then
		echo "Your host appears to have IPv6 connectivity."
		SUGGESTION="n"
	else
		echo "Your host does not appear to have IPv6 connectivity."
		SUGGESTION="n"
	fi
	echo ""
	# Ask the user if they want to enable IPv6 regardless its availability.
	until [[ $IPV6_SUPPORT =~ (y|n) ]]; do
		read -rp "Do you want to enable IPv6 support (NAT)? [y/n]: " -e -i $SUGGESTION IPV6_SUPPORT
	done
	echo ""
	echo "🔥 Dual Authentication Setup:"
	echo "This enhanced version will configure TWO OpenVPN servers simultaneously:"
	echo "  📜 Certificate-based: For professional users (PKI + TLS)"
	echo "  🔐 Username/Password: For simple users (PAM + TLS)"
	echo ""
	echo "Please configure ports and protocols for each authentication method:"
	echo ""
	
	# Certificate-based server configuration
	echo "=== Certificate-based Server Configuration ==="
	echo "What port do you want the Certificate-based server to listen on?"
	echo "   1) Default: 1194"
	echo "   2) Custom"
	echo "   3) Random [49152-65535]"
	until [[ $CERT_PORT_CHOICE =~ ^[1-3]$ ]]; do
		read -rp "Certificate server port choice [1-3]: " -e -i 1 CERT_PORT_CHOICE
	done
	case $CERT_PORT_CHOICE in
	1)
		CERT_PORT="1194"
		;;
	2)
		until [[ $CERT_PORT =~ ^[0-9]+$ ]] && [ "$CERT_PORT" -ge 1 ] && [ "$CERT_PORT" -le 65535 ]; do
			read -rp "Custom port for Certificate server [1-65535]: " -e -i 1194 CERT_PORT
		done
		;;
	3)
		CERT_PORT=$(shuf -i49152-65535 -n1)
		echo "Random Port for Certificate server: $CERT_PORT"
		;;
	esac
	
	echo ""
	echo "What protocol do you want the Certificate-based server to use?"
	echo "   1) UDP (Recommended - faster)"
	echo "   2) TCP"
	until [[ $CERT_PROTOCOL_CHOICE =~ ^[1-2]$ ]]; do
		read -rp "Certificate server protocol [1-2]: " -e -i 1 CERT_PROTOCOL_CHOICE
	done
	case $CERT_PROTOCOL_CHOICE in
	1)
		CERT_PROTOCOL="udp"
		;;
	2)
		CERT_PROTOCOL="tcp"
		;;
	esac
	
	echo ""
	echo "=== Username/Password Server Configuration ==="
	echo "What port do you want the Username/Password server to listen on?"
	echo "   1) Default: 1195"
	echo "   2) Custom"
	echo "   3) Random [49152-65535]"
	until [[ $LOGIN_PORT_CHOICE =~ ^[1-3]$ ]]; do
		read -rp "Login server port choice [1-3]: " -e -i 1 LOGIN_PORT_CHOICE
	done
	case $LOGIN_PORT_CHOICE in
	1)
		LOGIN_PORT="1195"
		;;
	2)
		until [[ $LOGIN_PORT =~ ^[0-9]+$ ]] && [ "$LOGIN_PORT" -ge 1 ] && [ "$LOGIN_PORT" -le 65535 ]; do
			read -rp "Custom port for Login server [1-65535]: " -e -i 1195 LOGIN_PORT
		done
		;;
	3)
		LOGIN_PORT=$(shuf -i49152-65535 -n1)
		echo "Random Port for Login server: $LOGIN_PORT"
		;;
	esac
	
	echo ""
	echo "What protocol do you want the Username/Password server to use?"
	echo "   1) UDP (Recommended - faster)"
	echo "   2) TCP"
	until [[ $LOGIN_PROTOCOL_CHOICE =~ ^[1-2]$ ]]; do
		read -rp "Login server protocol [1-2]: " -e -i 1 LOGIN_PROTOCOL_CHOICE
	done
	case $LOGIN_PROTOCOL_CHOICE in
	1)
		LOGIN_PROTOCOL="udp"
		;;
	2)
		LOGIN_PROTOCOL="tcp"
		;;
	esac
	
	# For backwards compatibility, set PORT and PROTOCOL to cert values
	PORT="$CERT_PORT"
	PROTOCOL="$CERT_PROTOCOL"
	
	echo ""
	echo "👍 Configuration Summary:"
	echo "  📜 Certificate-based: $CERT_PORT/$CERT_PROTOCOL"
	echo "  🔐 Username/Password: $LOGIN_PORT/$LOGIN_PROTOCOL"
	echo ""
	echo "What DNS resolvers do you want to use with the VPN?"
	echo "   1) Current system resolvers (from /etc/resolv.conf)"
	echo "   2) Self-hosted DNS Resolver (Unbound)"
	echo "   3) Cloudflare (Anycast: worldwide)"
	echo "   4) Quad9 (Anycast: worldwide)"
	echo "   5) Quad9 uncensored (Anycast: worldwide)"
	echo "   6) FDN (France)"
	echo "   7) DNS.WATCH (Germany)"
	echo "   8) OpenDNS (Anycast: worldwide)"
	echo "   9) Google (Anycast: worldwide)"
	echo "   10) Yandex Basic (Russia)"
	echo "   11) AdGuard DNS (Anycast: worldwide)"
	echo "   12) NextDNS (Anycast: worldwide)"
	echo "   13) Custom"
	until [[ $DNS =~ ^[0-9]+$ ]] && [ "$DNS" -ge 1 ] && [ "$DNS" -le 13 ]; do
		read -rp "DNS [1-12]: " -e -i 11 DNS
		if [[ $DNS == 2 ]] && [[ -e /etc/unbound/unbound.conf ]]; then
			echo ""
			echo "Unbound is already installed."
			echo "You can allow the script to configure it in order to use it from your OpenVPN clients"
			echo "We will simply add a second server to /etc/unbound/unbound.conf for the OpenVPN subnet."
			echo "No changes are made to the current configuration."
			echo ""

			until [[ $CONTINUE =~ (y|n) ]]; do
				read -rp "Apply configuration changes to Unbound? [y/n]: " -e CONTINUE
			done
			if [[ $CONTINUE == "n" ]]; then
				# Break the loop and cleanup
				unset DNS
				unset CONTINUE
			fi
		elif [[ $DNS == "13" ]]; then
			until [[ $DNS1 =~ ^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$ ]]; do
				read -rp "Primary DNS: " -e DNS1
			done
			until [[ $DNS2 =~ ^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$ ]]; do
				read -rp "Secondary DNS (optional): " -e DNS2
				if [[ $DNS2 == "" ]]; then
					break
				fi
			done
		fi
	done
	echo ""
	echo "Do you want to use compression? It is not recommended since the VORACLE attack makes use of it."
	until [[ $COMPRESSION_ENABLED =~ (y|n) ]]; do
		read -rp"Enable compression? [y/n]: " -e -i n COMPRESSION_ENABLED
	done
	if [[ $COMPRESSION_ENABLED == "y" ]]; then
		echo "Choose which compression algorithm you want to use: (they are ordered by efficiency)"
		echo "   1) LZ4-v2"
		echo "   2) LZ4"
		echo "   3) LZ0"
		until [[ $COMPRESSION_CHOICE =~ ^[1-3]$ ]]; do
			read -rp"Compression algorithm [1-3]: " -e -i 1 COMPRESSION_CHOICE
		done
		case $COMPRESSION_CHOICE in
		1)
			COMPRESSION_ALG="lz4-v2"
			;;
		2)
			COMPRESSION_ALG="lz4"
			;;
		3)
			COMPRESSION_ALG="lzo"
			;;
		esac
	fi
	echo ""
	echo "Do you want to customize encryption settings?"
	echo "Unless you know what you're doing, you should stick with the default parameters provided by the script."
	echo "Note that whatever you choose, all the choices presented in the script are safe (unlike OpenVPN's defaults)."
	echo "See https://github.com/angristan/openvpn-install#security-and-encryption to learn more."
	echo ""
	until [[ $CUSTOMIZE_ENC =~ (y|n) ]]; do
		read -rp "Customize encryption settings? [y/n]: " -e -i n CUSTOMIZE_ENC
	done
	if [[ $CUSTOMIZE_ENC == "n" ]]; then
		# Use default, sane and fast parameters
		CIPHER="AES-128-GCM"
		CERT_TYPE="1" # ECDSA
		CERT_CURVE="prime256v1"
		CC_CIPHER="TLS-ECDHE-ECDSA-WITH-AES-128-GCM-SHA256"
		DH_TYPE="1" # ECDH
		DH_CURVE="prime256v1"
		HMAC_ALG="SHA256"
		TLS_SIG="1" # tls-crypt
	else
		echo ""
		echo "Choose which cipher you want to use for the data channel:"
		echo "   1) AES-128-GCM (recommended)"
		echo "   2) AES-192-GCM"
		echo "   3) AES-256-GCM"
		echo "   4) AES-128-CBC"
		echo "   5) AES-192-CBC"
		echo "   6) AES-256-CBC"
		until [[ $CIPHER_CHOICE =~ ^[1-6]$ ]]; do
			read -rp "Cipher [1-6]: " -e -i 1 CIPHER_CHOICE
		done
		case $CIPHER_CHOICE in
		1)
			CIPHER="AES-128-GCM"
			;;
		2)
			CIPHER="AES-192-GCM"
			;;
		3)
			CIPHER="AES-256-GCM"
			;;
		4)
			CIPHER="AES-128-CBC"
			;;
		5)
			CIPHER="AES-192-CBC"
			;;
		6)
			CIPHER="AES-256-CBC"
			;;
		esac
		echo ""
		echo "Choose what kind of certificate you want to use:"
		echo "   1) ECDSA (recommended)"
		echo "   2) RSA"
		until [[ $CERT_TYPE =~ ^[1-2]$ ]]; do
			read -rp"Certificate key type [1-2]: " -e -i 1 CERT_TYPE
		done
		case $CERT_TYPE in
		1)
			echo ""
			echo "Choose which curve you want to use for the certificate's key:"
			echo "   1) prime256v1 (recommended)"
			echo "   2) secp384r1"
			echo "   3) secp521r1"
			until [[ $CERT_CURVE_CHOICE =~ ^[1-3]$ ]]; do
				read -rp"Curve [1-3]: " -e -i 1 CERT_CURVE_CHOICE
			done
			case $CERT_CURVE_CHOICE in
			1)
				CERT_CURVE="prime256v1"
				;;
			2)
				CERT_CURVE="secp384r1"
				;;
			3)
				CERT_CURVE="secp521r1"
				;;
			esac
			;;
		2)
			echo ""
			echo "Choose which size you want to use for the certificate's RSA key:"
			echo "   1) 2048 bits (recommended)"
			echo "   2) 3072 bits"
			echo "   3) 4096 bits"
			until [[ $RSA_KEY_SIZE_CHOICE =~ ^[1-3]$ ]]; do
				read -rp "RSA key size [1-3]: " -e -i 1 RSA_KEY_SIZE_CHOICE
			done
			case $RSA_KEY_SIZE_CHOICE in
			1)
				RSA_KEY_SIZE="2048"
				;;
			2)
				RSA_KEY_SIZE="3072"
				;;
			3)
				RSA_KEY_SIZE="4096"
				;;
			esac
			;;
		esac
		echo ""
		echo "Choose which cipher you want to use for the control channel:"
		case $CERT_TYPE in
		1)
			echo "   1) ECDHE-ECDSA-AES-128-GCM-SHA256 (recommended)"
			echo "   2) ECDHE-ECDSA-AES-256-GCM-SHA384"
			until [[ $CC_CIPHER_CHOICE =~ ^[1-2]$ ]]; do
				read -rp"Control channel cipher [1-2]: " -e -i 1 CC_CIPHER_CHOICE
			done
			case $CC_CIPHER_CHOICE in
			1)
				CC_CIPHER="TLS-ECDHE-ECDSA-WITH-AES-128-GCM-SHA256"
				;;
			2)
				CC_CIPHER="TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384"
				;;
			esac
			;;
		2)
			echo "   1) ECDHE-RSA-AES-128-GCM-SHA256 (recommended)"
			echo "   2) ECDHE-RSA-AES-256-GCM-SHA384"
			until [[ $CC_CIPHER_CHOICE =~ ^[1-2]$ ]]; do
				read -rp"Control channel cipher [1-2]: " -e -i 1 CC_CIPHER_CHOICE
			done
			case $CC_CIPHER_CHOICE in
			1)
				CC_CIPHER="TLS-ECDHE-RSA-WITH-AES-128-GCM-SHA256"
				;;
			2)
				CC_CIPHER="TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384"
				;;
			esac
			;;
		esac
		echo ""
		echo "Choose what kind of Diffie-Hellman key you want to use:"
		echo "   1) ECDH (recommended)"
		echo "   2) DH"
		until [[ $DH_TYPE =~ [1-2] ]]; do
			read -rp"DH key type [1-2]: " -e -i 1 DH_TYPE
		done
		case $DH_TYPE in
		1)
			echo ""
			echo "Choose which curve you want to use for the ECDH key:"
			echo "   1) prime256v1 (recommended)"
			echo "   2) secp384r1"
			echo "   3) secp521r1"
			while [[ $DH_CURVE_CHOICE != "1" && $DH_CURVE_CHOICE != "2" && $DH_CURVE_CHOICE != "3" ]]; do
				read -rp"Curve [1-3]: " -e -i 1 DH_CURVE_CHOICE
			done
			case $DH_CURVE_CHOICE in
			1)
				DH_CURVE="prime256v1"
				;;
			2)
				DH_CURVE="secp384r1"
				;;
			3)
				DH_CURVE="secp521r1"
				;;
			esac
			;;
		2)
			echo ""
			echo "Choose what size of Diffie-Hellman key you want to use:"
			echo "   1) 2048 bits (recommended)"
			echo "   2) 3072 bits"
			echo "   3) 4096 bits"
			until [[ $DH_KEY_SIZE_CHOICE =~ ^[1-3]$ ]]; do
				read -rp "DH key size [1-3]: " -e -i 1 DH_KEY_SIZE_CHOICE
			done
			case $DH_KEY_SIZE_CHOICE in
			1)
				DH_KEY_SIZE="2048"
				;;
			2)
				DH_KEY_SIZE="3072"
				;;
			3)
				DH_KEY_SIZE="4096"
				;;
			esac
			;;
		esac
		echo ""
		# The "auth" options behaves differently with AEAD ciphers
		if [[ $CIPHER =~ CBC$ ]]; then
			echo "The digest algorithm authenticates data channel packets and tls-auth packets from the control channel."
		elif [[ $CIPHER =~ GCM$ ]]; then
			echo "The digest algorithm authenticates tls-auth packets from the control channel."
		fi
		echo "Which digest algorithm do you want to use for HMAC?"
		echo "   1) SHA-256 (recommended)"
		echo "   2) SHA-384"
		echo "   3) SHA-512"
		until [[ $HMAC_ALG_CHOICE =~ ^[1-3]$ ]]; do
			read -rp "Digest algorithm [1-3]: " -e -i 1 HMAC_ALG_CHOICE
		done
		case $HMAC_ALG_CHOICE in
		1)
			HMAC_ALG="SHA256"
			;;
		2)
			HMAC_ALG="SHA384"
			;;
		3)
			HMAC_ALG="SHA512"
			;;
		esac
		echo ""
		echo "You can add an additional layer of security to the control channel with tls-auth and tls-crypt"
		echo "tls-auth authenticates the packets, while tls-crypt authenticate and encrypt them."
		echo "   1) tls-crypt (recommended)"
		echo "   2) tls-auth"
		until [[ $TLS_SIG =~ [1-2] ]]; do
			read -rp "Control channel additional security mechanism [1-2]: " -e -i 1 TLS_SIG
		done
	fi
	echo ""
	echo "Okay, that was all I needed. We are ready to setup your OpenVPN server now."
	echo "You will be able to generate a client at the end of the installation."
	APPROVE_INSTALL=${APPROVE_INSTALL:-n}
}

function installOpenVPN() {
	if [[ $AUTO_INSTALL == "y" ]]; then
		# Set default choices so that no questions will be asked.
		APPROVE_INSTALL=${APPROVE_INSTALL:-y}
		APPROVE_IP=${APPROVE_IP:-y}
		IPV6_SUPPORT=${IPV6_SUPPORT:-n}
		PORT_CHOICE=${PORT_CHOICE:-1}
		PROTOCOL_CHOICE=${PROTOCOL_CHOICE:-1}
		DNS=${DNS:-1}
		COMPRESSION_ENABLED=${COMPRESSION_ENABLED:-n}
		CUSTOMIZE_ENC=${CUSTOMIZE_ENC:-n}
		CLIENT=${CLIENT:-client}
		PASS=${PASS:-1}
		CONTINUE=${CONTINUE:-y}

		if [[ -z $ENDPOINT ]]; then
			ENDPOINT=$(resolvePublicIP)
		fi
	fi

	# Run setup questions first, and set other variables if auto-install
	installQuestions

	# Get the "public" interface from the default route
	NIC=$(ip -4 route ls | grep default | grep -Po '(?<=dev )(\S+)' | head -1)
	if [[ -z $NIC ]] && [[ $IPV6_SUPPORT == 'y' ]]; then
		NIC=$(ip -6 route show default | sed -ne 's/^default .* dev \([^ ]*\) .*$/\1/p')
	fi

	# $NIC can not be empty for script rm-openvpn-rules.sh
	if [[ -z $NIC ]]; then
		echo
		echo "Could not detect public interface."
		echo "This needs for setup MASQUERADE."
		until [[ $CONTINUE =~ (y|n) ]]; do
			read -rp "Continue? [y/n]: " -e CONTINUE
		done
		if [[ $CONTINUE == "n" ]]; then
			exit 1
		fi
	fi

	# If OpenVPN isn't installed yet, install it
	if [[ ! -e /etc/openvpn/server.conf ]]; then
		apt-get update
		apt-get -y install ca-certificates gnupg
		
		# For Ubuntu 16.04, add OpenVPN repository
		if [[ $VERSION_ID == "16.04" ]]; then
			echo "deb http://build.openvpn.net/debian/openvpn/stable xenial main" >/etc/apt/sources.list.d/openvpn.list
			wget -O - https://swupdate.openvpn.net/repos/repo-public.gpg | apt-key add -
			apt-get update
		fi
		
		# Install OpenVPN and dependencies
		apt-get install -y openvpn iptables openssl wget ca-certificates curl
		
		# Remove old easy-rsa if exists
		if [[ -d /etc/openvpn/easy-rsa/ ]]; then
			rm -rf /etc/openvpn/easy-rsa/
		fi
	fi

	# Find out if the machine uses nogroup or nobody for the permissionless group
	if grep -qs "^nogroup:" /etc/group; then
		NOGROUP=nogroup
	else
		NOGROUP=nobody
	fi

	# Install the latest version of easy-rsa from source, if not already installed.
	if [[ ! -d /etc/openvpn/easy-rsa/ ]]; then
		local version="3.1.2"
		wget -O ~/easy-rsa.tgz https://github.com/OpenVPN/easy-rsa/releases/download/v${version}/EasyRSA-${version}.tgz
		mkdir -p /etc/openvpn/easy-rsa
		tar xzf ~/easy-rsa.tgz --strip-components=1 --no-same-owner --directory /etc/openvpn/easy-rsa
		rm -f ~/easy-rsa.tgz

		cd /etc/openvpn/easy-rsa/ || return
		case $CERT_TYPE in
		1)
			echo "set_var EASYRSA_ALGO ec" >vars
			echo "set_var EASYRSA_CURVE $CERT_CURVE" >>vars
			;;
		2)
			echo "set_var EASYRSA_KEY_SIZE $RSA_KEY_SIZE" >vars
			;;
		esac

		# Generate a random, alphanumeric identifier of 16 characters for CN and one for server name
		SERVER_CN="cn_$(head /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)"
		echo "$SERVER_CN" >SERVER_CN_GENERATED
		SERVER_NAME="server_$(head /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)"
		echo "$SERVER_NAME" >SERVER_NAME_GENERATED

		# Create the PKI, set up the CA, the DH params and the server certificate
		./easyrsa init-pki
		EASYRSA_CA_EXPIRE=3650 ./easyrsa --batch --req-cn="$SERVER_CN" build-ca nopass

		if [[ $DH_TYPE == "2" ]]; then
			# ECDH keys are generated on-the-fly so we don't need to generate them beforehand
			openssl dhparam -out dh.pem $DH_KEY_SIZE
		fi

		EASYRSA_CERT_EXPIRE=3650 ./easyrsa --batch build-server-full "$SERVER_NAME" nopass
		EASYRSA_CRL_DAYS=3650 ./easyrsa gen-crl

		case $TLS_SIG in
		1)
			# Generate tls-crypt key
			openvpn --genkey --secret /etc/openvpn/tls-crypt.key
			;;
		2)
			# Generate tls-auth key
			openvpn --genkey --secret /etc/openvpn/tls-auth.key
			;;
		esac
	else
		cd /etc/openvpn/easy-rsa/ || return
		SERVER_NAME=$(cat SERVER_NAME_GENERATED)
	fi

	cp pki/ca.crt pki/private/ca.key "pki/issued/$SERVER_NAME.crt" "pki/private/$SERVER_NAME.key" /etc/openvpn/easy-rsa/pki/crl.pem /etc/openvpn
	if [[ $DH_TYPE == "2" ]]; then
		cp dh.pem /etc/openvpn
	fi

	chmod 644 /etc/openvpn/crl.pem

	echo "port $PORT" >/etc/openvpn/server.conf
	if [[ $IPV6_SUPPORT == 'n' ]]; then
		echo "proto $PROTOCOL" >>/etc/openvpn/server.conf
	elif [[ $IPV6_SUPPORT == 'y' ]]; then
		echo "proto ${PROTOCOL}6" >>/etc/openvpn/server.conf
	fi

	echo "dev tun
user nobody
group $NOGROUP
persist-key
persist-tun
keepalive 10 120
topology subnet
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist ipp.txt" >>/etc/openvpn/server.conf

	echo 'push "redirect-gateway def1 bypass-dhcp"' >>/etc/openvpn/server.conf
	if [[ $IPV6_SUPPORT == 'y' ]]; then
		echo 'server-ipv6 fd42:42:42:42::/112
tun-ipv6
push tun-ipv6
push "route-ipv6 2000::/3"
push "redirect-gateway ipv6"' >>/etc/openvpn/server.conf
	fi

	if [[ $COMPRESSION_ENABLED == "y" ]]; then
		echo "compress $COMPRESSION_ALG" >>/etc/openvpn/server.conf
	fi

	if [[ $DH_TYPE == "1" ]]; then
		echo "dh none" >>/etc/openvpn/server.conf
		echo "ecdh-curve $DH_CURVE" >>/etc/openvpn/server.conf
	elif [[ $DH_TYPE == "2" ]]; then
		echo "dh dh.pem" >>/etc/openvpn/server.conf
	fi

	case $TLS_SIG in
	1)
		echo "tls-crypt tls-crypt.key" >>/etc/openvpn/server.conf
		;;
	2)
		echo "tls-auth tls-auth.key 0" >>/etc/openvpn/server.conf
		;;
	esac

	echo "crl-verify crl.pem
ca ca.crt
cert $SERVER_NAME.crt
key $SERVER_NAME.key
auth $HMAC_ALG
cipher $CIPHER
ncp-ciphers $CIPHER
tls-server
tls-version-min 1.2
tls-cipher $CC_CIPHER
client-config-dir /etc/openvpn/ccd
status /var/log/openvpn/status.log
verb 3" >>/etc/openvpn/server.conf

	mkdir -p /etc/openvpn/ccd
	mkdir -p /var/log/openvpn

	echo 'net.ipv4.ip_forward=1' >/etc/sysctl.d/99-openvpn.conf
	if [[ $IPV6_SUPPORT == 'y' ]]; then
		echo 'net.ipv6.conf.all.forwarding=1' >>/etc/sysctl.d/99-openvpn.conf
	fi
	sysctl --system

	if hash sestatus 2>/dev/null; then
		if sestatus | grep "Current mode" | grep -qs "enforcing"; then
			if [[ $PORT != '1194' ]]; then
				semanage port -a -t openvpn_port_t -p "$PROTOCOL" "$PORT"
			fi
		fi
	fi

	if [[ $VERSION_ID != "16.04" ]]; then
		cp /lib/systemd/system/openvpn\@.service /etc/systemd/system/openvpn\@.service

		sed -i 's|LimitNPROC|#LimitNPROC|' /etc/systemd/system/openvpn\@.service
		sed -i 's|/etc/openvpn/server|/etc/openvpn|' /etc/systemd/system/openvpn\@.service

		systemctl daemon-reload
	fi
	
	if [[ $DNS == 2 ]]; then
		installUnbound
	fi

	mkdir -p /etc/iptables

	if [[ $IPV6_SUPPORT == 'y' ]]; then
		echo "ip6tables -t nat -D POSTROUTING -s fd42:42:42:42::/112 -o $NIC -j MASQUERADE
ip6tables -D INPUT -i tun0 -j ACCEPT
ip6tables -D FORWARD -i $NIC -o tun0 -j ACCEPT
ip6tables -D FORWARD -i tun0 -o $NIC -j ACCEPT
ip6tables -D INPUT -i $NIC -p $PROTOCOL --dport $PORT -j ACCEPT" >>/etc/iptables/rm-openvpn-rules.sh
	fi

	echo "[Unit]
Description=iptables rules for OpenVPN
After=network-online.target openvpn@server-cert.service openvpn@server-login.service
Wants=network-online.target openvpn@server-cert.service openvpn@server-login.service

[Service]
Type=oneshot
ExecStart=/etc/iptables/add-openvpn-rules.sh
ExecStop=/etc/iptables/rm-openvpn-rules.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target" >/etc/systemd/system/iptables-openvpn.service

	systemctl daemon-reload
	systemctl enable iptables-openvpn

	if [[ $ENDPOINT != "" ]]; then
		IP=$ENDPOINT
	fi

	echo "client" >/etc/openvpn/client-template.txt
	if [[ $PROTOCOL == 'udp' ]]; then
		echo "proto udp" >>/etc/openvpn/client-template.txt
		echo "explicit-exit-notify" >>/etc/openvpn/client-template.txt
	elif [[ $PROTOCOL == 'tcp' ]]; then
		echo "proto tcp-client" >>/etc/openvpn/client-template.txt
	fi
	echo "remote $IP $PORT
dev tun
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
verify-x509-name $SERVER_NAME name
auth $HMAC_ALG
auth-nocache
cipher $CIPHER
tls-client
tls-version-min 1.2
tls-cipher $CC_CIPHER
ignore-unknown-option block-outside-dns
setenv opt block-outside-dns # Prevent Windows 10 DNS leak
verb 3" >>/etc/openvpn/client-template.txt

	if [[ $COMPRESSION_ENABLED == "y" ]]; then
		echo "compress $COMPRESSION_ALG" >>/etc/openvpn/client-template.txt
	fi

	echo ""
	echo "Setting up dual authentication (Certificate + Username/Password)..."
	
	installPAMPlugin
	
	createDualServerConfigs
	
	setupDualSystemdServices
	
	# Save server IP for future use
	if [[ -n $ENDPOINT ]]; then
		echo "$ENDPOINT" > /etc/openvpn/server_ip.conf
	elif [[ -n $IP ]]; then
		echo "$IP" > /etc/openvpn/server_ip.conf
	fi
	
	generateSharedLoginConfig
	
	# Install ovpn command globally
	cp "$0" /usr/local/bin/ovpn
	chmod +x /usr/local/bin/ovpn
	
	clear
	manageMenu
}

function revokeCertClient() {
    local USERNAME="$1"
    if [[ "$USERNAME" == "main" ]]; then
        echo "Error: Cannot remove main certificate (required for login-based authentication)"
        return 1
    fi
    if [[ -e /etc/openvpn/easy-rsa/pki/index.txt ]]; then
        if grep -q "/CN=$USERNAME$" /etc/openvpn/easy-rsa/pki/index.txt; then
            cd /etc/openvpn/easy-rsa/ || return
            ./easyrsa --batch revoke "$USERNAME" >/dev/null 2>&1
            EASYRSA_CRL_DAYS=3650 ./easyrsa gen-crl >/dev/null 2>&1
            rm -f /etc/openvpn/crl.pem
            cp /etc/openvpn/easy-rsa/pki/crl.pem /etc/openvpn/crl.pem
            chmod 644 /etc/openvpn/crl.pem
            if ./easyrsa --help 2>&1 | grep -q 'remove'; then
                ./easyrsa --batch remove "$USERNAME" >/dev/null 2>&1
            else
                sed -i "/CN=$USERNAME$/d" /etc/openvpn/easy-rsa/pki/index.txt
            fi
        fi
        rm -f "/etc/openvpn/clients/${USERNAME}-cert.ovpn"
        rm -f "/etc/openvpn/easy-rsa/pki/issued/${USERNAME}.crt"
        rm -f "/etc/openvpn/easy-rsa/pki/private/${USERNAME}.key"
        rm -f "/etc/openvpn/easy-rsa/pki/reqs/${USERNAME}.req"
        if [[ -e /etc/openvpn/easy-rsa/pki/index.txt.attr ]]; then
            sed -i "/$USERNAME/d" /etc/openvpn/easy-rsa/pki/index.txt.attr
        fi
    fi
}

function revokeLoginUser() {
    local USERNAME="$1"
    if [[ -e /etc/openvpn/login-users.txt ]]; then
        sed -i "/^$USERNAME$/d" /etc/openvpn/login-users.txt
        if id "$USERNAME" &>/dev/null; then
            userdel "$USERNAME" >/dev/null 2>&1
        fi
    fi
}

function revokeUser() {
    if [[ ! -e /etc/openvpn/easy-rsa/pki/index.txt && ! -e /etc/openvpn/login-users.txt ]]; then
        echo "No users found!"
        return
    fi
    echo ""
    echo "Select the user you want to remove:"
    local users=()
    if [[ -e /etc/openvpn/easy-rsa/pki/index.txt ]]; then
        mapfile -t cert_users < <(tail -n +2 /etc/openvpn/easy-rsa/pki/index.txt | grep "^V" | cut -d '=' -f 2 | grep -v "^main$")
        users+=("${cert_users[@]}")
    fi
    if [[ -e /etc/openvpn/login-users.txt ]]; then
        mapfile -t login_users < <(cat /etc/openvpn/login-users.txt)
        for u in "${login_users[@]}"; do
            if [[ ! " ${users[*]} " =~ " $u " ]]; then
                users+=("$u")
            fi
        done
    fi
    if [[ ${#users[@]} -eq 0 ]]; then
        echo "No users found!"
        return
    fi
    for i in "${!users[@]}"; do
        printf "%d) %s\n" $((i+1)) "${users[$i]}"
    done
    echo "0) Back"
    local USERNUMBER
    until [[ "$USERNUMBER" =~ ^[0-9]+$ && $USERNUMBER -ge 0 && $USERNUMBER -le ${#users[@]} ]]; do
        read -rp "Select one user [0-${#users[@]}]: " USERNUMBER
    done
    if [[ "$USERNUMBER" == "0" ]]; then
        returnToMenu
        return
    fi
    local USERNAME="${users[$((USERNUMBER-1))]}"
    revokeCertClient "$USERNAME"
    revokeLoginUser "$USERNAME"
    # Double-check removal
    if grep -q "/CN=$USERNAME$" /etc/openvpn/easy-rsa/pki/index.txt 2>/dev/null || grep -q "^$USERNAME$" /etc/openvpn/login-users.txt 2>/dev/null; then
        echo "Warning: User $USERNAME was not fully removed. Please check manually."
    else
        echo "User $USERNAME removed."
    fi
    returnToMenu
}

function generateSharedLoginConfig() {
    local CLIENTS_DIR="/etc/openvpn/clients"
    mkdir -p "$CLIENTS_DIR"
    chmod 700 "$CLIENTS_DIR"
    local config_file="$CLIENTS_DIR/main.ovpn"
    if [[ ! -e /etc/openvpn/easy-rsa/pki/issued/main.crt || ! -e /etc/openvpn/easy-rsa/pki/private/main.key ]]; then
        cd /etc/openvpn/easy-rsa/ || return 1
        EASYRSA_CERT_EXPIRE=3650 ./easyrsa --batch build-client-full main nopass >/dev/null 2>&1
    fi
    if [[ ! -e /etc/openvpn/easy-rsa/pki/issued/main.crt || ! -e /etc/openvpn/easy-rsa/pki/private/main.key ]]; then
        echo "[ERROR] main certificate or key not found. Cannot generate main.ovpn." >&2
        return 1
    fi
    if [[ ! -e $config_file ]]; then
        if [[ -e /etc/openvpn/server-login.conf ]]; then
            server_port=$(grep '^port ' /etc/openvpn/server-login.conf | cut -d ' ' -f 2)
            server_protocol=$(grep '^proto ' /etc/openvpn/server-login.conf | cut -d ' ' -f 2)
            if [[ -e /etc/openvpn/server_ip.conf ]]; then
                server_ip=$(cat /etc/openvpn/server_ip.conf)
            elif [[ -n $ENDPOINT ]]; then
                server_ip="$ENDPOINT"
            elif [[ -n $IP ]]; then
                server_ip="$IP"
            else
                server_ip=$(hostname -I | awk '{print $1}')
                if [[ -z "$server_ip" ]]; then
                    server_ip="YOUR_SERVER_IP"
                fi
            fi
        else
            server_port="1195"
            server_protocol="udp"
            server_ip=$(hostname -I | awk '{print $1}')
            if [[ -z "$server_ip" ]]; then
                server_ip="YOUR_SERVER_IP"
            fi
        fi
        local cipher="AES-256-GCM"
        local auth="SHA256"
        if [[ -n $CIPHER ]]; then
            cipher="$CIPHER"
        fi
        if [[ -n $HMAC_ALG ]]; then
            auth="$HMAC_ALG"
        fi
        cat > "$config_file" << EOF
client
dev tun
proto $server_protocol
remote $server_ip $server_port
resolv-retry infinite
nobind
persist-key
persist-tun
auth-user-pass
remote-cert-tls server
verb 3
cipher $cipher
auth $auth
tls-version-min 1.2
<ca>
EOF
        cat /etc/openvpn/easy-rsa/pki/ca.crt >> "$config_file"
        echo "</ca>" >> "$config_file"
        echo "<cert>" >> "$config_file"
        awk '/BEGIN/,/END CERTIFICATE/' /etc/openvpn/easy-rsa/pki/issued/main.crt >> "$config_file"
        echo "</cert>" >> "$config_file"
        echo "<key>" >> "$config_file"
        cat /etc/openvpn/easy-rsa/pki/private/main.key >> "$config_file"
        echo "</key>" >> "$config_file"
        if grep -q "^tls-crypt" /etc/openvpn/server-login.conf 2>/dev/null; then
            echo "<tls-crypt>" >> "$config_file"
            cat /etc/openvpn/tls-crypt.key >> "$config_file"
            echo "</tls-crypt>" >> "$config_file"
        elif grep -q "^tls-auth" /etc/openvpn/server-login.conf 2>/dev/null; then
            echo "<tls-auth>" >> "$config_file"
            if [[ -e /etc/openvpn/tls-auth-login.key ]]; then
                cat /etc/openvpn/tls-auth-login.key >> "$config_file"
            else
                cat /etc/openvpn/tls-auth.key >> "$config_file"
            fi
            echo "</tls-auth>" >> "$config_file"
            echo "key-direction 1" >> "$config_file"
        fi
    fi
}

function createLoginUser() {
    local USERNAME="$1"
    local PASSWORD="$2"
    if id "$USERNAME" &>/dev/null; then
        echo "$PASSWORD" | passwd --stdin "$USERNAME" >/dev/null 2>&1 || echo -e "$PASSWORD\n$PASSWORD" | passwd "$USERNAME" >/dev/null 2>&1
    else
        useradd -s /bin/false -M "$USERNAME" >/dev/null 2>&1
        echo "$PASSWORD" | passwd --stdin "$USERNAME" >/dev/null 2>&1 || echo -e "$PASSWORD\n$PASSWORD" | passwd "$USERNAME" >/dev/null 2>&1
    fi
    if [[ ! -e /etc/openvpn/login-users.txt ]]; then
        touch /etc/openvpn/login-users.txt
    fi
    if ! grep -q "^$USERNAME$" /etc/openvpn/login-users.txt; then
        echo "$USERNAME" >> /etc/openvpn/login-users.txt
    fi
    generateSharedLoginConfig
    local CLIENTS_DIR="/etc/openvpn/clients"
    echo "[INFO] Login-based config: $CLIENTS_DIR/main.ovpn"
}

function listClients() {
    echo ""
    echo "=== OpenVPN Client List ==="
    echo ""
    
    echo "📜 Certificate-based clients:"
    if [[ -e /etc/openvpn/easy-rsa/pki/index.txt ]]; then
        CERT_CLIENTS=$(tail -n +2 /etc/openvpn/easy-rsa/pki/index.txt | grep "^V" | cut -d '=' -f 2)
        if [[ -n $CERT_CLIENTS ]]; then
            echo "$CERT_CLIENTS" | nl -s ') '
        else
            echo "  No certificate-based clients found."
        fi
    else
        echo "  Certificate system not initialized."
    fi
    
    echo ""
    
    echo "🔐 Login-based users:"
    if [[ -e /etc/openvpn/login-users.txt ]]; then
        if [[ -s /etc/openvpn/login-users.txt ]]; then
            cat /etc/openvpn/login-users.txt | nl -s ') '
        else
            echo "  No login-based users found."
        fi
    else
        echo "  Login-based authentication not configured."
    fi
    
    returnToMenu
}



function installPAMPlugin() {
	echo "Installing PAM authentication plugin..."
    
	apt-get update
	apt-get install -y libpam-modules
	
	cat > /etc/pam.d/openvpn << 'EOF'
auth    required    pam_unix.so shadow nodelay
account required    pam_unix.so
EOF
	
	echo "PAM authentication configured for OpenVPN."
}

function createDualServerConfigs() {
	echo "Creating dual server configurations..."
	
	NIC=$(ip -4 route ls | grep default | grep -Po '(?<=dev )(\S+)' | head -1)
	
	createCertServerConfig
	
	createLoginServerConfig
	
	applyDNSConfiguration
	
	updateIptablesForDual
	
	echo "Server configurations created."
}

function createCertServerConfig() {
	local config_file="/etc/openvpn/server-cert.conf"
	
	if [[ -e /etc/openvpn/server.conf ]]; then
		cp /etc/openvpn/server.conf "$config_file"
		sed -i "s/^port .*/port $CERT_PORT/" "$config_file"
		sed -i "s/^proto .*/proto $CERT_PROTOCOL/" "$config_file"
		sed -i "s/^dev .*/dev tun0/" "$config_file"
		sed -i "s/^ifconfig-pool-persist .*/ifconfig-pool-persist ipp-cert.txt/" "$config_file"
		sed -i "s|^status .*|status /var/log/openvpn/status-cert.log|" "$config_file"
	fi
}

function applyDNSConfiguration() {
	local cert_config="/etc/openvpn/server-cert.conf"
	local login_config="/etc/openvpn/server-login.conf"
	
	sed -i '/^push.*dhcp-option DNS/d' "$cert_config" 2>/dev/null || true
	sed -i '/^push.*dhcp-option DNS/d' "$login_config" 2>/dev/null || true
	
	case $DNS in
	1)
		local resolvers=()
		mapfile -t resolvers < <(grep nameserver /etc/resolv.conf | cut -d ' ' -f 2)
		for resolver in "${resolvers[@]}"; do
			echo "push \"dhcp-option DNS $resolver\"" >> "$cert_config"
			echo "push \"dhcp-option DNS $resolver\"" >> "$login_config"
		done
		;;
	2)
		echo 'push "dhcp-option DNS 10.8.0.1"' >> "$cert_config"
		echo 'push "dhcp-option DNS 10.9.0.1"' >> "$login_config"
		;;
	3)
		echo 'push "dhcp-option DNS 1.1.1.1"' >> "$cert_config"
		echo 'push "dhcp-option DNS 1.0.0.1"' >> "$login_config"
		echo 'push "dhcp-option DNS 1.1.1.1"' >> "$login_config"
		echo 'push "dhcp-option DNS 1.0.0.1"' >> "$cert_config"
		;;
	4)
		echo 'push "dhcp-option DNS 9.9.9.9"' >> "$cert_config"
		echo 'push "dhcp-option DNS 149.112.112.112"' >> "$cert_config"
		echo 'push "dhcp-option DNS 9.9.9.9"' >> "$login_config"
		echo 'push "dhcp-option DNS 149.112.112.112"' >> "$login_config"
		;;
	5)
		echo 'push "dhcp-option DNS 9.9.9.10"' >> "$cert_config"
		echo 'push "dhcp-option DNS 149.112.112.10"' >> "$cert_config"
		echo 'push "dhcp-option DNS 9.9.9.10"' >> "$login_config"
		echo 'push "dhcp-option DNS 149.112.112.10"' >> "$login_config"
		;;
	6)
		echo 'push "dhcp-option DNS 80.67.169.40"' >> "$cert_config"
		echo 'push "dhcp-option DNS 80.67.169.12"' >> "$cert_config"
		echo 'push "dhcp-option DNS 80.67.169.40"' >> "$login_config"
		echo 'push "dhcp-option DNS 80.67.169.12"' >> "$login_config"
		;;
	7)
		echo 'push "dhcp-option DNS 84.200.69.80"' >> "$cert_config"
		echo 'push "dhcp-option DNS 84.200.70.40"' >> "$cert_config"
		echo 'push "dhcp-option DNS 84.200.69.80"' >> "$login_config"
		echo 'push "dhcp-option DNS 84.200.70.40"' >> "$login_config"
		;;
	8)
		echo 'push "dhcp-option DNS 208.67.222.222"' >> "$cert_config"
		echo 'push "dhcp-option DNS 208.67.220.220"' >> "$cert_config"
		echo 'push "dhcp-option DNS 208.67.222.222"' >> "$login_config"
		echo 'push "dhcp-option DNS 208.67.220.220"' >> "$login_config"
		;;
	9)
		echo 'push "dhcp-option DNS 8.8.8.8"' >> "$cert_config"
		echo 'push "dhcp-option DNS 8.8.4.4"' >> "$cert_config"
		echo 'push "dhcp-option DNS 8.8.8.8"' >> "$login_config"
		echo 'push "dhcp-option DNS 8.8.4.4"' >> "$login_config"
		;;
	10)
		echo 'push "dhcp-option DNS 77.88.8.8"' >> "$cert_config"
		echo 'push "dhcp-option DNS 77.88.8.1"' >> "$cert_config"
		echo 'push "dhcp-option DNS 77.88.8.8"' >> "$login_config"
		echo 'push "dhcp-option DNS 77.88.8.1"' >> "$login_config"
		;;
	11)
		echo 'push "dhcp-option DNS 94.140.14.14"' >> "$cert_config"
		echo 'push "dhcp-option DNS 94.140.15.15"' >> "$cert_config"
		echo 'push "dhcp-option DNS 94.140.14.14"' >> "$login_config"
		echo 'push "dhcp-option DNS 94.140.15.15"' >> "$login_config"
		;;
	12)
		echo 'push "dhcp-option DNS 45.90.28.167"' >> "$cert_config"
		echo 'push "dhcp-option DNS 45.90.30.167"' >> "$cert_config"
		echo 'push "dhcp-option DNS 45.90.28.167"' >> "$login_config"
		echo 'push "dhcp-option DNS 45.90.30.167"' >> "$login_config"
		;;
	13)
		echo "push \"dhcp-option DNS $DNS1\"" >> "$cert_config"
		echo "push \"dhcp-option DNS $DNS1\"" >> "$login_config"
		if [[ $DNS2 != "" ]]; then
			echo "push \"dhcp-option DNS $DNS2\"" >> "$cert_config"
			echo "push \"dhcp-option DNS $DNS2\"" >> "$login_config"
		fi
		;;
	esac
}

function createLoginServerConfig() {
	local config_file="/etc/openvpn/server-login.conf"
	
	local server_name
	if [[ -e /etc/openvpn/easy-rsa/SERVER_NAME_GENERATED ]]; then
		server_name=$(cat /etc/openvpn/easy-rsa/SERVER_NAME_GENERATED)
	else
		echo "Error: SERVER_NAME_GENERATED not found"
		return 1
	fi
	
	local dh_config
	local ecdh_config
	if [[ $DH_TYPE == "1" ]]; then
		dh_config="dh none"
		ecdh_config="ecdh-curve ${DH_CURVE:-prime256v1}"
	elif [[ $DH_TYPE == "2" ]]; then
		dh_config="dh /etc/openvpn/dh.pem"
		ecdh_config=""
	else
		dh_config="dh none"
		ecdh_config="ecdh-curve prime256v1"
	fi
	
	local tls_config
	case $TLS_SIG in
	1)
		tls_config="tls-crypt /etc/openvpn/tls-crypt.key"
		;;
	2)
		tls_config="tls-auth /etc/openvpn/tls-auth-login.key 0"
		;;
	*)
		tls_config="tls-auth /etc/openvpn/tls-auth-login.key 0"
		;;
	esac
    
	local cipher_config="${CIPHER:-AES-256-GCM:AES-128-GCM}"
	local cc_cipher_config="${CC_CIPHER:-TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384:TLS-ECDHE-RSA-WITH-CHACHA20-POLY1305-SHA256:TLS-ECDHE-RSA-WITH-AES-128-GCM-SHA256:TLS-ECDHE-RSA-WITH-AES-256-CBC-SHA384}"
	
	cat > "$config_file" << EOF
port $LOGIN_PORT
proto $LOGIN_PROTOCOL
dev tun1
ca /etc/openvpn/ca.crt
cert /etc/openvpn/$server_name.crt
key /etc/openvpn/$server_name.key
$dh_config
$(if [[ -n "$ecdh_config" ]]; then echo "$ecdh_config"; fi)
server 10.9.0.0 255.255.255.0
ifconfig-pool-persist ipp-login.txt

# PAM authentication  
plugin /usr/lib/x86_64-linux-gnu/openvpn/plugins/openvpn-plugin-auth-pam.so openvpn
username-as-common-name
verify-client-cert none

push "redirect-gateway def1 bypass-dhcp"
keepalive 10 120

# CRL verification
crl-verify /etc/openvpn/crl.pem
$tls_config
ncp-ciphers $cipher_config
tls-server
tls-version-min 1.2
tls-cipher $cc_cipher_config
client-config-dir /etc/openvpn/ccd
user nobody
group ${NOGROUP:-nogroup}
persist-key
persist-tun
status /var/log/openvpn/status-login.log
verb 3
EOF

	if [[ ! -e /etc/openvpn/tls-auth-login.key ]]; then
		openvpn --genkey --secret /etc/openvpn/tls-auth-login.key
		echo "Generated TLS auth key for login server."
	fi
}

function updateIptablesForDual() {
	mkdir -p /etc/iptables
	
	cat > /etc/iptables/add-openvpn-rules.sh << EOF
#!/bin/sh
# Certificate-based server (tun0, 10.8.0.0/24)
iptables -t nat -I POSTROUTING 1 -s 10.8.0.0/24 -o $NIC -j MASQUERADE
iptables -I INPUT 1 -i tun0 -j ACCEPT
iptables -I FORWARD 1 -i $NIC -o tun0 -j ACCEPT
iptables -I FORWARD 1 -i tun0 -o $NIC -j ACCEPT
iptables -I INPUT 1 -i $NIC -p $CERT_PROTOCOL --dport $CERT_PORT -j ACCEPT

# Login-based server (tun1, 10.9.0.0/24)
iptables -t nat -I POSTROUTING 1 -s 10.9.0.0/24 -o $NIC -j MASQUERADE
iptables -I INPUT 1 -i tun1 -j ACCEPT
iptables -I FORWARD 1 -i $NIC -o tun1 -j ACCEPT
iptables -I FORWARD 1 -i tun1 -o $NIC -j ACCEPT
iptables -I INPUT 1 -i $NIC -p $LOGIN_PROTOCOL --dport $LOGIN_PORT -j ACCEPT
EOF

	cat > /etc/iptables/rm-openvpn-rules.sh << EOF
#!/bin/sh
# Certificate-based server
iptables -t nat -D POSTROUTING -s 10.8.0.0/24 -o $NIC -j MASQUERADE
iptables -D INPUT -i tun0 -j ACCEPT
iptables -D FORWARD -i $NIC -o tun0 -j ACCEPT
iptables -D FORWARD -i tun0 -o $NIC -j ACCEPT
iptables -D INPUT -i $NIC -p $CERT_PROTOCOL --dport $CERT_PORT -j ACCEPT

# Login-based server
iptables -t nat -D POSTROUTING -s 10.9.0.0/24 -o $NIC -j MASQUERADE
iptables -D INPUT -i tun1 -j ACCEPT
iptables -D FORWARD -i $NIC -o tun1 -j ACCEPT
iptables -D FORWARD -i tun1 -o $NIC -j ACCEPT
iptables -D INPUT -i $NIC -p $LOGIN_PROTOCOL --dport $LOGIN_PORT -j ACCEPT
EOF

	chmod +x /etc/iptables/add-openvpn-rules.sh
	chmod +x /etc/iptables/rm-openvpn-rules.sh
	echo "iptables rules scripts created and made executable."
	
	/etc/iptables/add-openvpn-rules.sh
}

function setupDualSystemdServices() {
	echo "Setting up systemd services for dual authentication..."
	
	if [[ $VERSION_ID == "16.04" ]]; then
		systemctl enable openvpn
		systemctl start openvpn
	else
		if systemctl is-active --quiet openvpn@server; then
			systemctl stop openvpn@server
			systemctl disable openvpn@server
		fi
		
		systemctl enable openvpn@server-cert
		systemctl enable openvpn@server-login
		systemctl start openvpn@server-cert
		systemctl start openvpn@server-login
	fi
	
	touch /etc/openvpn/login-users.txt
	systemctl start iptables-openvpn
	

}

function removeUnbound() {
	sed -i '/include: \/etc\/unbound\/openvpn.conf/d' /etc/unbound/unbound.conf
	rm /etc/unbound/openvpn.conf

	until [[ $REMOVE_UNBOUND =~ (y|n) ]]; do
		echo ""
		echo "If you were already using Unbound before installing OpenVPN, I removed the configuration related to OpenVPN."
		read -rp "Do you want to completely remove Unbound? [y/n]: " -e REMOVE_UNBOUND
	done

	if [[ $REMOVE_UNBOUND == 'y' ]]; then
		systemctl stop unbound

		apt-get remove --purge -y unbound

		rm -rf /etc/unbound/

		echo ""
		echo "Unbound removed!"
	else
		systemctl restart unbound
		echo ""
		echo "Unbound wasn't removed."
	fi
}

function removeOpenVPN() {
	echo ""
			read -rp "Do you really want to remove OpenVPN? [y/n]: " -e -i y REMOVE
	if [[ $REMOVE == 'y' ]]; then
		PORT=$(grep '^port ' /etc/openvpn/server.conf | cut -d " " -f 2)
		PROTOCOL=$(grep '^proto ' /etc/openvpn/server.conf | cut -d " " -f 2)

		if [[ $VERSION_ID == "16.04" ]]; then
			systemctl disable openvpn
			systemctl stop openvpn
		else
			if systemctl is-active --quiet openvpn@server-cert; then
				systemctl disable openvpn@server-cert
				systemctl stop openvpn@server-cert
			fi
			if systemctl is-active --quiet openvpn@server-login; then
				systemctl disable openvpn@server-login
				systemctl stop openvpn@server-login
			fi
			if systemctl is-active --quiet openvpn@server; then
				systemctl disable openvpn@server
				systemctl stop openvpn@server
				rm -f /etc/systemd/system/openvpn\@.service
			fi
		fi

		systemctl stop iptables-openvpn
		systemctl disable iptables-openvpn
		rm /etc/systemd/system/iptables-openvpn.service
		systemctl daemon-reload
		rm /etc/iptables/add-openvpn-rules.sh
		rm /etc/iptables/rm-openvpn-rules.sh

		if hash sestatus 2>/dev/null; then
			if sestatus | grep "Current mode" | grep -qs "enforcing"; then
				if [[ $PORT != '1194' ]]; then
					semanage port -d -t openvpn_port_t -p "$PROTOCOL" "$PORT"
				fi
			fi
		fi

		find /home/ -maxdepth 2 -name "*.ovpn" -delete
		find /root/ -maxdepth 1 -name "*.ovpn" -delete
		
		rm -rf /var/log/openvpn
		rm -rf /etc/openvpn
		rm -rf /etc/iptables/add-openvpn-rules.sh
		rm -rf /etc/iptables/rm-openvpn-rules.sh
		
		apt-get remove --purge -y openvpn
		if [[ -e /etc/apt/sources.list.d/openvpn.list ]]; then
			rm /etc/apt/sources.list.d/openvpn.list
			apt-get update
		fi
		rm -rf /usr/share/doc/openvpn*
		rm -f /etc/sysctl.d/99-openvpn.conf
		rm -rf /var/log/openvpn
		
		if [[ -e /etc/openvpn/login-users.txt ]]; then
			while read -r username; do
				if id "$username" &>/dev/null; then
					userdel "$username" 2>/dev/null
				fi
			done < /etc/openvpn/login-users.txt
		fi

		if [[ -e /etc/unbound/openvpn.conf ]]; then
			removeUnbound
		fi
		echo ""
		echo "OpenVPN removed!"
	else
		echo ""
		echo "Removal aborted!"
	fi
}

function manageMenu() {
	echo "OpenVPN Dual Auth Installer"
	echo "Repository: https://github.com/smaghili/openvpn"
	echo ""
	
	# Get actual ports from config files
	local cert_port="1194"
	local login_port="1195"
	local cert_protocol="UDP"
	local login_protocol="UDP"
	
	if [[ -e /etc/openvpn/server-cert.conf ]]; then
		cert_port=$(grep '^port ' /etc/openvpn/server-cert.conf | cut -d ' ' -f 2)
		cert_protocol=$(grep '^proto ' /etc/openvpn/server-cert.conf | cut -d ' ' -f 2 | tr '[:lower:]' '[:upper:]')
	fi
	
	if [[ -e /etc/openvpn/server-login.conf ]]; then
		login_port=$(grep '^port ' /etc/openvpn/server-login.conf | cut -d ' ' -f 2)
		login_protocol=$(grep '^proto ' /etc/openvpn/server-login.conf | cut -d ' ' -f 2 | tr '[:lower:]' '[:upper:]')
	fi
	
	echo "OpenVPN is running with dual authentication support:"
	echo "  📜 Certificate-based: Port $cert_port/$cert_protocol (Professional users)"
	echo "  🔐 Username/Password: Port $login_port/$login_protocol (Simple users)"
	echo ""
	
	echo "What do you want to do?"
	echo "   1) Add a new user"
	echo "   2) Remove user"
	echo "   3) List all clients"
	echo "   4) Remove OpenVPN"
	echo "   5) Exit"
	until [[ $MENU_OPTION =~ ^[1-5]$ ]]; do
		read -rp "Select an option [1-5]: " MENU_OPTION
	done

	case $MENU_OPTION in
	1)
		addUserDual
		;;
	2)
		revokeUser
		;;
	3)
		listClients
		;;
	4)
		removeOpenVPN
		;;
	5)
		exit 0
		;;
	esac
}

function returnToMenu() {
    echo ""
    read -rp "Press Enter to continue..."
    MENU_OPTION=""
    manageMenu
}

function createCertUser() {
    local USERNAME="$1"
    local CLIENTS_DIR="/etc/openvpn/clients"
    mkdir -p "$CLIENTS_DIR"
    chmod 700 "$CLIENTS_DIR"
    CLIENTEXISTS=$(tail -n +2 /etc/openvpn/easy-rsa/pki/index.txt | grep -c -E "/CN=$USERNAME\$")
    if [[ $CLIENTEXISTS == '1' ]]; then
        echo "Error: Username '$USERNAME' already exists as a certificate user."
        return 1
    else
        cd /etc/openvpn/easy-rsa/ || return
        EASYRSA_CERT_EXPIRE=3650 ./easyrsa --batch build-client-full "$USERNAME" nopass >/dev/null 2>&1
    fi
    local homeDir="$CLIENTS_DIR"
    cp /etc/openvpn/client-template.txt "$homeDir/$USERNAME-cert.ovpn"
    {
        echo "<ca>"
        cat "/etc/openvpn/easy-rsa/pki/ca.crt"
        echo "</ca>"
        echo "<cert>"
        awk '/BEGIN/,/END CERTIFICATE/' "/etc/openvpn/easy-rsa/pki/issued/$USERNAME.crt"
        echo "</cert>"
        echo "<key>"
        cat "/etc/openvpn/easy-rsa/pki/private/$USERNAME.key"
        echo "</key>"
        if grep -qs "^tls-crypt" /etc/openvpn/server.conf; then
            echo "<tls-crypt>"
            cat /etc/openvpn/tls-crypt.key
            echo "</tls-crypt>"
        elif grep -qs "^tls-auth" /etc/openvpn/server.conf; then
            echo "key-direction 1"
            echo "<tls-auth>"
            cat /etc/openvpn/tls-auth.key
            echo "</tls-auth>"
        fi
    } >>"$homeDir/$USERNAME-cert.ovpn"
    echo "[INFO] Cert-based config: $homeDir/$USERNAME-cert.ovpn"
}

function addUserDual() {
    USERNAME=""
    until [[ $USERNAME =~ ^[a-zA-Z0-9_-]+$ ]]; do
        read -rp "Username: " -e USERNAME
        if [[ -z "$USERNAME" ]]; then
            echo ""
            MENU_OPTION=""
            manageMenu
            return
        fi
    done
    read -s -rp "Password: " PASSWORD
    echo
    createCertUser "$USERNAME"
    createLoginUser "$USERNAME" "$PASSWORD"
    returnToMenu
}

initialCheck

# Install ovpn command globally if not exists
if [[ ! -e /usr/local/bin/ovpn ]]; then
	cp "$0" /usr/local/bin/ovpn
	chmod +x /usr/local/bin/ovpn
fi

if [[ (-e /etc/openvpn/server-cert.conf && -e /etc/openvpn/server-login.conf) || (-e /etc/openvpn/server.conf) ]] && [[ $AUTO_INSTALL != "y" ]]; then
	manageMenu
else
	installOpenVPN
fi
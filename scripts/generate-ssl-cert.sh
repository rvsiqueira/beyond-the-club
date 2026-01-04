#!/bin/bash
# Generate self-signed SSL certificate for Cloudflare Full SSL mode
# For production, use Cloudflare Origin Certificate instead (recommended)

set -e

SSL_DIR="nginx/ssl"
DOMAIN="${1:-beyondtheclub.local}"

echo "=== SSL Certificate Generator for Cloudflare Full Mode ==="
echo ""
echo "For PRODUCTION, you should use a Cloudflare Origin Certificate:"
echo "1. Go to Cloudflare Dashboard > SSL/TLS > Origin Server"
echo "2. Click 'Create Certificate'"
echo "3. Download the certificate and private key"
echo "4. Save them as:"
echo "   - nginx/ssl/origin.pem (certificate)"
echo "   - nginx/ssl/origin-key.pem (private key)"
echo ""
echo "This script generates a SELF-SIGNED certificate for testing only."
echo ""

read -p "Generate self-signed certificate for testing? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted. Please use Cloudflare Origin Certificate for production."
    exit 0
fi

mkdir -p "$SSL_DIR"

echo "Generating self-signed certificate for: $DOMAIN"

# Generate private key
openssl genrsa -out "$SSL_DIR/origin-key.pem" 2048

# Generate certificate signing request
openssl req -new -key "$SSL_DIR/origin-key.pem" \
    -out "$SSL_DIR/origin.csr" \
    -subj "/C=BR/ST=Sao Paulo/L=Sao Paulo/O=Beyond The Club/CN=$DOMAIN"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 \
    -in "$SSL_DIR/origin.csr" \
    -signkey "$SSL_DIR/origin-key.pem" \
    -out "$SSL_DIR/origin.pem"

# Cleanup CSR
rm "$SSL_DIR/origin.csr"

# Set permissions
chmod 600 "$SSL_DIR/origin-key.pem"
chmod 644 "$SSL_DIR/origin.pem"

echo ""
echo "=== Certificate generated successfully ==="
echo "  Certificate: $SSL_DIR/origin.pem"
echo "  Private Key: $SSL_DIR/origin-key.pem"
echo ""
echo "IMPORTANT: For production, replace these with Cloudflare Origin Certificate!"
echo ""
echo "Next steps:"
echo "1. In Cloudflare Dashboard, set SSL/TLS mode to 'Full'"
echo "2. Run: docker-compose --profile production up -d"

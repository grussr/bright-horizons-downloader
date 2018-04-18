cat << EOF > /app/key.json
{
  "type": "service_account",
  "project_id": "$gcs_project_id",
  "private_key_id": "$gcs_private_key_id",
  "private_key": "$gcs_private_key",
  "client_email": "$gcs_client_email",
  "client_id": "$gcs_client_id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://accounts.google.com/o/oauth2/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "$gcs_client_x509_cert_url"
}
EOF

export GOOGLE_APPLICATION_CREDENTIALS=/app/key.json
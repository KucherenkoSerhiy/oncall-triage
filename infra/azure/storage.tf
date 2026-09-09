# Storage account backing both Function apps' control-plane data (triggers,
# locks, WEBSITE_RUN_FROM_PACKAGE) - required by every plan including
# Consumption (Y1); shared because one account per app would double the
# ~$0.20/month always-there cost for no isolation benefit at this scale.

resource "random_string" "storage_suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_storage_account" "functions" {
  name                = "nordwindtriage${random_string.storage_suffix.result}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location

  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  allow_nested_items_to_be_public = false

  # Y1 (Consumption) Function apps authenticate to their own control-plane
  # storage with an account key (storage_account_access_key on each function
  # app below) - Azure has no managed-identity path for that connection on
  # this plan, so the key must stay enabled. Documented again in
  # infra/README.md.
  shared_access_key_enabled = true

  tags = local.tags.monitor
}

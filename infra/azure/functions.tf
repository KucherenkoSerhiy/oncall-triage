# Observability backing the two Function apps: a Log Analytics workspace
# (daily_quota_gb caps ingestion so verbose logging can't run away with the
# bill - see docs/DESIGN.md's cost model) and a workspace-based Application
# Insights component with sampling on. Both feed the alert rules in
# alerts.tf.

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.name_prefix}-logs"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location

  sku               = "PerGB2018"
  retention_in_days = 30
  daily_quota_gb    = 0.2

  tags = local.tags.monitor
}

resource "azurerm_application_insights" "main" {
  name                = "${local.name_prefix}-appinsights"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location

  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  sampling_percentage = 20

  tags = local.tags.monitor
}

resource "azurerm_service_plan" "functions" {
  name                = "${local.name_prefix}-plan"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location

  os_type  = "Linux"
  sku_name = "Y1"

  tags = local.tags.monitor
}

# ---------------------------------------------------------------- packaging
# Each app deploys standalone: its own bank/azure/<app>/ directory plus
# bank/azure/_shared/ copied in as a sibling folder at the zip root (see
# bank/azure/README.md's "sibling-import trick"). archive_file has no way to
# merge two source directories, so the file list is built by hand from
# fileset() over both directories.

locals {
  bank_azure_dir = "${path.module}/../../bank/azure"

  function_apps = {
    notifications = "customer_notifications"
    forwarder     = "alert_forwarder"
  }

  zip_files = {
    for app, dir in local.function_apps : app => merge(
      {
        for f in fileset("${local.bank_azure_dir}/${dir}", "**") :
        f => "${local.bank_azure_dir}/${dir}/${f}"
        if !can(regex("__pycache__|\\.pyc$", f))
      },
      {
        for f in fileset("${local.bank_azure_dir}/_shared", "**") :
        "_shared/${f}" => "${local.bank_azure_dir}/_shared/${f}"
        if !can(regex("__pycache__|\\.pyc$", f))
      }
    )
  }
}

data "archive_file" "functions" {
  for_each = local.zip_files

  type        = "zip"
  output_path = "${path.module}/build/${each.key}.zip"

  dynamic "source" {
    for_each = each.value
    content {
      filename = source.key
      content  = file(source.value)
    }
  }
}

# ---------------------------------------------------------------- customer-notifications

resource "azurerm_linux_function_app" "notifications" {
  name                = "${local.name_prefix}-notifications"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location

  service_plan_id            = azurerm_service_plan.functions.id
  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key

  https_only = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    ftps_state                             = "Disabled"
    minimum_tls_version                    = "1.2"

    application_stack {
      python_version = "3.12"
    }
  }

  # CONSOLE_TOKEN/INGEST_HMAC_SECRET land here as plaintext app settings -
  # the accepted v1 trade-off (infra/README.md, mirrors the Lambda
  # environment on AWS). WEBSITE_RUN_FROM_PACKAGE + SCM_DO_BUILD_DURING_DEPLOYMENT
  # make Oryx install requirements.txt from the zip_deploy_file below.
  app_settings = {
    CHAOS_URL                      = "https://api.triage.serhiykucherenko.dev/chaos"
    CONSOLE_TOKEN                  = var.console_token
    WEBSITE_RUN_FROM_PACKAGE       = "1"
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true"
  }

  zip_deploy_file = data.archive_file.functions["notifications"].output_path

  tags = local.tags.notifications
}

# ---------------------------------------------------------------- alert-forwarder

resource "azurerm_linux_function_app" "forwarder" {
  name                = "${local.name_prefix}-forwarder"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location

  service_plan_id            = azurerm_service_plan.functions.id
  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key

  https_only = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    ftps_state                             = "Disabled"
    minimum_tls_version                    = "1.2"

    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    INGEST_URL                     = "https://api.triage.serhiykucherenko.dev/alerts"
    INGEST_HMAC_SECRET             = var.ingest_hmac_secret
    WEBSITE_RUN_FROM_PACKAGE       = "1"
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true"
  }

  zip_deploy_file = data.archive_file.functions["forwarder"].output_path

  tags = local.tags.forwarder
}

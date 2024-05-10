#
# az login
# az account set --subscription "e1da45af-3c03-4ba1-8df1-0d122aab1cb4"
#
# export ARM_CLIENT_ID="<APPID_VALUE>"
# export ARM_CLIENT_SECRET="<PASSWORD_VALUE>"
# export ARM_SUBSCRIPTION_ID="<SUBSCRIPTION_ID>"
# export ARM_TENANT_ID="<TENANT_VALUE>"
#
# terraform init
# terraform apply
#
terraform {
  required_version = ">= 1.4"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "3.102.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "Bi4Common"
    storage_account_name = "terraformbackendssa"
    container_name       = "nahv"
    key                  = "ow.terraform.tfstate"
    subscription_id = "e1da45af-3c03-4ba1-8df1-0d122aab1cb4" # Can also be set via `ARM_SUBSCRIPTION_ID` envar.
    tenant_id            = "a924227e-3ef4-426c-8c8d-931f5666f9f6" # Can also be set via `ARM_TENANT_ID` envar.
  }
}

provider "azurerm" {
  features {}
  skip_provider_registration = true
}

data "azurerm_client_config" "this" {}

locals {
  project_name_alnum = replace(var.project_name, "-", "")
}

################################################################################################################
# resources for testing
################################################################################################################
resource "azurerm_resource_group" "tmp" {
  name     = var.resource_group_name
  location = var.location
}
resource "azurerm_virtual_network" "tmp" {
  name                = "${var.project_name}-net"
  location            = azurerm_resource_group.tmp.location
  resource_group_name = var.resource_group_name
  address_space       = ["10.0.0.0/16"]
}
resource "azurerm_subnet" "tmp" {
  name                 = "${var.project_name}-tmp-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.tmp.name
  address_prefixes     = ["10.0.2.0/24"]
  service_endpoints    = ["Microsoft.Storage"]
  delegation {
    name = "fs"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}
resource "azurerm_private_dns_zone" "tmp" {
  name                = "${var.project_name}.postgres.database.azure.com"
  resource_group_name = var.resource_group_name
}
resource "azurerm_private_dns_zone_virtual_network_link" "tmp" {
  name                  = "thisVnetZone.com"
  private_dns_zone_name = azurerm_private_dns_zone.tmp.name
  virtual_network_id    = azurerm_virtual_network.tmp.id
  resource_group_name   = var.resource_group_name
  depends_on            = [azurerm_subnet.tmp]
}
resource "azurerm_postgresql_flexible_server" "tmp" {
  name                   = "db-test-delete"
  resource_group_name    = var.resource_group_name
  location               = azurerm_resource_group.tmp.location
  version                = "14"
  delegated_subnet_id    = azurerm_subnet.tmp.id
  private_dns_zone_id    = azurerm_private_dns_zone.tmp.id
  administrator_login    = "psqladmin"
  administrator_password = "H@Sh1CoR3!"
  zone                   = "2"

  storage_mb   = 32768
  storage_tier = "P4"

  sku_name   = "B_Standard_B1ms"
  depends_on = [azurerm_private_dns_zone_virtual_network_link.tmp]
}

resource "azurerm_key_vault" "tmp" {
  name                       = "nahv-kv-delete"
  location                   = azurerm_resource_group.tmp.location
  resource_group_name        = var.resource_group_name
  tenant_id                  = data.azurerm_client_config.this.tenant_id
  soft_delete_retention_days = 7
  sku_name                   = "standard"
}

locals {
  tmp_name_key_vault = "nahv-kv-delete" # "nahv-kv-tendertool"
  tmp_name_db_server = "db-test-delete" # "nahv-psql-tendertool-vvez"
  tmp_name_vnet = azurerm_virtual_network.tmp.name # "nahv-vnet-tendertool"
  tmp_db_id = azurerm_postgresql_flexible_server.tmp.id
  # "${azurerm_resource_group.tmp.id}/providers/Microsoft.DBforPostgreSQL/flexibleServers/nahv-psql-tendertool-vvez"
  tmp_name_storage_account = "terraformbackendssa" # "nahvsttendertoolvvez"
}
################################################################################################################
#
################################################################################################################

resource "azurerm_storage_share" "this" {
  name                 = "${var.project_name}-data"
  storage_account_name = local.tmp_name_storage_account
  quota                = 500
  access_tier          = "TransactionOptimized"
}

resource "azurerm_service_plan" "this" {
  name                = "${var.project_name}-plan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "B1"
}


resource "azurerm_subnet" "this" {
  name                 = "${var.project_name}-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = local.tmp_name_vnet
  address_prefixes     = ["10.0.5.0/24"] # TODOFR: try to get from current virtual network

  delegation {
    name = "Microsoft.Web.serverFarms"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }

  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.Web"
  ]
}

resource "azurerm_linux_web_app" "this" {
  name                = "${var.project_name}"
  resource_group_name = var.resource_group_name
  location            = azurerm_service_plan.this.location
  service_plan_id     = azurerm_service_plan.this.id

  app_settings = {
    "AZURE_OPENAI_API_BASE_URL"          = "https://nucleoo-ai-gpt4.openai.azure.com"
    "AZURE_OPENAI_API_KEY"               = "@Microsoft.KeyVault(VaultName=${local.tmp_name_key_vault};SecretName=OWUI-AZURE-OPENAI-API-KEY)"
    "AZURE_OPENAI_DEPLOYMENT_MODEL_NAME" = "nucleoo-ai-gpt4-32k"
    "DATA_DIR"                           = "/data"
    "DATABASE_URL"                       = "@Microsoft.KeyVault(VaultName=${local.tmp_name_key_vault};SecretName=OWUI-DB-STRING)"
    "OPENAI_API_KEY"                     = "@Microsoft.KeyVault(VaultName=${local.tmp_name_key_vault};SecretName=OWUI-OPENAI-API-KEY)"
    "WEBUI_NAME"                         = "NAHV Private Chat"
    # "WEBSITES_ENABLE_APP_SERVICE_STORAGE": "false",
    # "DOCKER_ENABLE_CI": "true", # TODOFR: find setting continuous deploy: ON
  }

  https_only = true

  site_config {
    always_on = false
    # worker_count = 1
    container_registry_use_managed_identity = false

    application_stack {
      docker_image_name   = "${var.project_name}-api:latest"
      docker_registry_url = "https://${azurerm_container_registry.this.login_server}"
    }
  }

  logs {
    detailed_error_messages = false
    failed_request_tracing  = false

    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }

  storage_account {
    access_key = "asdfdasfadsfadsfadsf" # TODOFR: "4auytYbxnjvTDiRyZ4HK5+E9/5KPU0----, how to get the key?
    account_name = local.tmp_name_storage_account
    name         = "data"
    mount_path   = "/data"
    share_name   = azurerm_storage_share.this.name
    type         = "AzureFiles"
  }

  virtual_network_subnet_id                = azurerm_subnet.this.id
  ftp_publish_basic_authentication_enabled = false

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_container_registry" "this" {
  name                = "${local.project_name_alnum}reg"
  admin_enabled       = true
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Basic"
}

resource "azurerm_container_registry_webhook" "this" {
  name                = "${local.project_name_alnum}webhook"
  location            = var.location
  resource_group_name = var.resource_group_name
  registry_name       = azurerm_container_registry.this.name
  actions             = ["push"]
  scope               = "${var.project_name}:latest"
  service_uri         = "https://${azurerm_linux_web_app.this.site_credential[0].name}:${azurerm_linux_web_app.this.site_credential[0].password}@${var.project_name}.scm.azurewebsites.net/api/registry/webhook"
}

resource "azurerm_key_vault_access_policy" "this" {
  key_vault_id = azurerm_key_vault.tmp.id
  tenant_id    = azurerm_linux_web_app.this.identity[0].tenant_id
  object_id    = azurerm_linux_web_app.this.identity[0].principal_id

  secret_permissions = [
    "Get"
  ]
}

resource "azurerm_key_vault_secret" "this1" {
  key_vault_id = azurerm_key_vault.tmp.id
  name         = "OWUI-AZURE-OPENAI-API-KEY"
  value        = "XXXXXX"
}
resource "azurerm_key_vault_secret" "this2" {
  key_vault_id = azurerm_key_vault.tmp.id
  name         = "OWUI-DB-STRING"
  value        = "XXXXXX"
}
resource "azurerm_key_vault_secret" "this3" {
  key_vault_id = azurerm_key_vault.tmp.id
  name         = "OWUI-OPENAI-API-KEY"
  value        = "XXXXXX"
}

resource "azurerm_postgresql_flexible_server_database" "this" {
  name      = var.project_name
  server_id = local.tmp_db_id
  collation = "en_US.utf8"
  charset   = "utf8"

  lifecycle {
    prevent_destroy = true
  }
}

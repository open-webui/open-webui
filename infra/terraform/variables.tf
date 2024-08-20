variable "region" {
  type = string
}

variable "availability_zones" {
  type = list(string)
}

variable "default_security_group_deny_all" {
  type = bool
}

variable "default_route_table_no_routes" {
  type = bool
}

variable "default_network_acl_deny_all" {
  type = bool
}

variable "network_address_usage_metrics_enabled" {
  type = bool
}

variable "resource_group_name" {
  type        = string
  description = "The name of the resource group, for example: 'my-resource-group'"
  nullable    = false
  default     = "nahv-chat-owui-test"
}

variable "project_name" {
  type        = string
  description = "The name of the project, for example: 'my-project'"
  nullable    = false
  default     = "nahv-chat-owui"
}

variable "location" {
  type        = string
  description = "The location in which deploy the infrastructure, for example: 'West Europe'"
  nullable    = false
  default     = "West Europe"
}

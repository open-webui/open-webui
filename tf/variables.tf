variable "boundary_policy_arn" {
  default = ""
}

variable "namespace" {
  description = "Kubernetes namespace"
  default     = "open-webui"
}

variable "service_account_name" {
  description = "Kubernetes ServiceAccount name"
  default     = "open-webui"
}

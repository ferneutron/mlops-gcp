variable "project_id" {
    description = "project_id"
    type = string
    sensitive = true
}

variable "location" {
    description = "location"
    type = string
    sensitive = true
}

variable "service_account_key" {
    description = "service_account_key"
    sensitive = true
}

variable "service_account_name" {
    description = "service_account_name"
    type = string
    sensitive = true
}

variable "roles_list" {
    description = "roles_list"
    type = list(string)
    sensitive = false
}

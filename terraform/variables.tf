variable "proxmox_endpoint" {
  description = "Proxmox VE API endpoint"
  type        = string
}

variable "proxmox_node" {
  description = "Proxmox node on which the virtual machines will be created"
  type        = string
}

variable "vm_name" {
  description = "Name of the virtual machine"
  type        = string
  default     = "liora-k8s-node"
}

variable "vm_cpu_cores" {
  description = "Number of CPU cores assigned to the virtual machine"
  type        = number
  default     = 2
}

variable "vm_memory" {
  description = "Memory assigned to the virtual machine in MB"
  type        = number
  default     = 4096
}

variable "vm_disk_size" {
  description = "Disk size of the virtual machine in GB"
  type        = number
  default     = 20
}
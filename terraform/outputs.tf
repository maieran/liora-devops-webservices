output "vm_name" {
  description = "Name of the created Kubernetes VM"
  value       = proxmox_vm_qemu.k8s_node.name
}

output "vm_id" {
  description = "Proxmox VM ID"
  value       = proxmox_vm_qemu.k8s_node.vmid
}

output "target_node" {
  description = "Proxmox node hosting the VM"
  value       = proxmox_vm_qemu.k8s_node.target_node
}
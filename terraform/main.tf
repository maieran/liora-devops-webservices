resource "proxmox_vm_qemu" "k8s_node" {
  name        = var.vm_name
  target_node = var.proxmox_node

  agent   = 1
  qemu_os = "other"

  iso = "local:iso/ubuntu-24.04.4-live-server-amd64.iso"

  cores  = var.vm_cpu_cores
  memory = var.vm_memory

  scsihw = "virtio-scsi-single"

  disk {
    type    = "scsi"
    storage = "vmdata"
    size    = "${var.vm_disk_size}G"
  }

  network {
    model  = "virtio"
    bridge = "vmbr1"
  }

  lifecycle {
    ignore_changes = [
      disk
    ]
  }
}
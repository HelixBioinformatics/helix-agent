#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a /var/log/helix-bootstrap.log) 2>&1
export DEBIAN_FRONTEND=noninteractive
ROLE='@@ROLE@@'
NODE='@@NODE@@'
HEAD_IP='@@HEAD_IP@@'
WORKER1_IP='@@WORKER1_IP@@'
WORKER2_IP='@@WORKER2_IP@@'
SUBNET_CIDR='@@SUBNET_CIDR@@'
hostnamectl set-hostname "$NODE"
install -d /etc/cloud/cloud.cfg.d
cat > /etc/cloud/cloud.cfg.d/99-helix-hostname.cfg <<'EOF'
preserve_hostname: true
manage_etc_hosts: false
EOF
cat >> /etc/hosts <<EOF
$HEAD_IP helix-head
$WORKER1_IP helix-worker1
$WORKER2_IP helix-worker2
EOF

# Each boot gets at most three hours. EC2 is configured to STOP on guest shutdown.
# This timer does not assume Academy sessions or credentials last indefinitely.
cat > /etc/systemd/system/helix-session-stop.service <<'EOF'
[Unit]
Description=Stop this thesis node to preserve Academy credits
[Service]
Type=oneshot
ExecStart=/usr/sbin/poweroff
EOF
cat > /etc/systemd/system/helix-session-stop.timer <<'EOF'
[Unit]
Description=Three hour maximum runtime per thesis node boot
[Timer]
OnBootSec=180min
AccuracySec=30s
Unit=helix-session-stop.service
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now helix-session-stop.timer

apt-get update -q
apt-get install -y --no-install-recommends slurm-wlm munge nfs-common nfs-kernel-server docker.io openjdk-21-jre-headless python3 python3-venv curl ca-certificates jq rsync
systemctl stop slurmd slurmctld munge || true
usermod -aG docker ubuntu
install -d -o munge -g munge -m 0700 /etc/munge
printf '%s' '@@MUNGE_KEY_BASE64@@' | base64 --decode > /etc/munge/munge.key
chown munge:munge /etc/munge/munge.key
chmod 0400 /etc/munge/munge.key
install -d -o slurm -g slurm -m 0755 /var/spool/slurmctld /var/log/slurm
install -d -o root -g root -m 0755 /var/spool/slurmd /etc/slurm /shared/helix
cat > /etc/slurm/slurm.conf <<EOF
ClusterName=helix-academy
SlurmctldHost=helix-head($HEAD_IP)
SlurmUser=slurm
SlurmctldPort=6817
SlurmdPort=6818
AuthType=auth/munge
StateSaveLocation=/var/spool/slurmctld
SlurmdSpoolDir=/var/spool/slurmd
SwitchType=switch/none
MpiDefault=none
ProctrackType=proctrack/cgroup
TaskPlugin=task/cgroup,task/affinity
JobAcctGatherType=jobacct_gather/cgroup
JobAcctGatherFrequency=10
SchedulerType=sched/backfill
SelectType=select/cons_tres
SelectTypeParameters=CR_Core_Memory
ReturnToService=2
SlurmctldLogFile=/var/log/slurm/slurmctld.log
SlurmdLogFile=/var/log/slurm/slurmd.log
AccountingStorageType=accounting_storage/none
JobCompType=jobcomp/filetxt
JobCompLoc=/var/log/slurm/completed-jobs.log
NodeName=helix-worker1 NodeAddr=$WORKER1_IP CPUs=2 Boards=1 SocketsPerBoard=1 CoresPerSocket=1 ThreadsPerCore=2 RealMemory=7400 State=UNKNOWN
NodeName=helix-worker2 NodeAddr=$WORKER2_IP CPUs=2 Boards=1 SocketsPerBoard=1 CoresPerSocket=1 ThreadsPerCore=2 RealMemory=7400 State=UNKNOWN
PartitionName=helix Nodes=helix-worker[1-2] Default=YES MaxTime=00:20:00 DefMemPerCPU=1024 MaxMemPerNode=7000 State=UP
EOF
cat > /etc/slurm/cgroup.conf <<'EOF'
CgroupPlugin=autodetect
ConstrainCores=yes
ConstrainRAMSpace=yes
ConstrainSwapSpace=yes
EOF

if [[ "$ROLE" == head ]]; then
    install -d -o ubuntu -g ubuntu -m 0755 /srv/helix
    install -d /etc/exports.d
    printf '/srv/helix %s(rw,sync,no_subtree_check,root_squash)\n' "$SUBNET_CIDR" > /etc/exports.d/helix.exports
    grep -Fqx '/srv/helix /shared/helix none bind 0 0' /etc/fstab || printf '/srv/helix /shared/helix none bind 0 0\n' >> /etc/fstab
    mount /shared/helix
    exportfs -ra
    systemctl enable --now nfs-server
    systemctl disable slurmd
    systemctl enable --now munge docker slurmctld
    curl --fail --location --retry 3 'https://github.com/nextflow-io/nextflow/releases/download/v25.10.4/nextflow-25.10.4-dist' -o /usr/local/bin/nextflow
    chmod 0755 /usr/local/bin/nextflow
else
    NFS_ENTRY="$HEAD_IP:/srv/helix /shared/helix nfs4 rw,_netdev,nofail,x-systemd.automount,x-systemd.mount-timeout=60s 0 0"
    grep -Fqx "$NFS_ENTRY" /etc/fstab || printf '%s\n' "$NFS_ENTRY" >> /etc/fstab
    mkdir -p /etc/systemd/system/slurmd.service.d
    cat > /etc/systemd/system/slurmd.service.d/helix.conf <<'EOF'
[Unit]
After=network-online.target munge.service
Wants=network-online.target
RequiresMountsFor=/shared/helix
[Service]
Delegate=yes
Restart=on-failure
RestartSec=15
EOF
    systemctl disable slurmctld nfs-server
    systemctl daemon-reload
    systemctl enable --now munge docker slurmd
fi
dpkg-query -W > /var/log/helix-installed-packages.tsv
touch /var/lib/helix-bootstrap-ready
echo 'HELIX_BOOTSTRAP_READY'

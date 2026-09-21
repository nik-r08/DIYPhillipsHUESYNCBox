#!/usr/bin/env bash
# 24 h soak / 4 h thermal logger (T6, T8). Every 30 s: temp, throttle flags, CPU, memory, HyperHDR restarts.
#   nohup tools/tests/soak_logger.sh soak.csv 24 &
OUT=${1:-soak.csv}; HOURS=${2:-24}; USER_=$(ls /home | head -1)
END=$(( $(date +%s) + HOURS*3600 ))
echo "timestamp,temp_c,throttled,cpu_pct,mem_used_mb,hyperhdr_active,hyperhdr_starts,load1" >> "$OUT"
while [ "$(date +%s)" -lt "$END" ]; do
  T=$(vcgencmd measure_temp 2>/dev/null | tr -dc '0-9.')
  TH=$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)
  CPU=$(top -bn1 | awk '/Cpu\(s\)/{print 100-$8}')
  MEM=$(free -m | awk '/Mem:/{print $3}')
  ACT=$(systemctl is-active "hyperhdr@${USER_}" 2>/dev/null)
  ST=$(journalctl -u "hyperhdr@${USER_}" --no-pager 2>/dev/null | grep -c 'Started')
  L1=$(cut -d' ' -f1 /proc/loadavg)
  echo "$(date '+%F %T'),$T,$TH,$CPU,$MEM,$ACT,$ST,$L1" >> "$OUT"
  sleep 30
done
echo "soak finished. Summary:"
awk -F, 'NR>1{ if($2>max)max=$2; if($3!="0x0")thr++; st=$7 } END{printf "max temp %.1f C, throttled samples %d, hyperhdr starts %d\n", max, thr, st}' "$OUT"

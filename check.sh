for n in $(seq 1 50); do c=$(curl -s -o /dev/null -w "%{http_code}" https://media.pinkmoonhouse.com/justmates/ep$n/master.m3u8); [ "$c" = 200 ] || echo "ep$n master $c"; done
curl -sI -H "Origin: https://pinkmoonhouse.com" https://media.pinkmoonhouse.com/justmates/ep41/master.m3u8 | grep -i "http/\|access-control\|content-type\|cache"
curl -s https://media.pinkmoonhouse.com/justmates/ep41/master.m3u8
curl -sI -H "Origin: https://pinkmoonhouse.com" https://media.pinkmoonhouse.com/justmates/ep41/v0/s000.ts | grep -i "http/\|access-control\|content-type\|content-length"
echo checked

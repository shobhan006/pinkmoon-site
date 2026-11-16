for u in justmates/ep5/master.m3u8 justmates/ep5/v0/index.m3u8 justmates/ep5/v0/s000.ts; do
  for k in 1 2 3; do curl -s -o /dev/null -D - -w "time %{time_total}s\n" -H "Origin: https://pinkmoonhouse.com" https://media.pinkmoonhouse.com/$u | grep -i "^http/\|cf-cache-status\|^time\|cache-control"; done; echo "--"; done
echo checked
for u in https://pinkmoonhouse.com/films/pinkmoon-loop.mp4 https://pinkmoonhouse.com/films/m/pinkmoon-loop.mp4 https://pinkmoonhouse.com/films/m/pinkmoon-loop-portrait.mp4 https://pinkmoonhouse.com/ ; do curl -s -o /dev/null -w "$u %{http_code} %{size_download} %{content_type} %{time_total}s\n" $u; done
curl -s https://pinkmoonhouse.com/ | grep -o 'pinkmoon-loop[^"]*' | sort -u

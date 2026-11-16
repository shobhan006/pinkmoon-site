#!/bin/bash
# encode mode: every episode -> adaptive HLS (native full quality + 960p-ish + 640p), uploaded to R2;
# plus 12s silent previews for new episodes, committed back to this branch
set -u
P=$(jq -r .prefix job.json); FROM=$(jq -r '.previewsFrom // 41' job.json)
mkdir -p hls previews
jq -e .files job.json >/dev/null || aws s3 rm s3://pinkmoon/$P/ --recursive --endpoint-url $R2 --only-show-errors
: > report.txt
for f in /tmp/src/*; do
  n=$(basename "$f" | sed -n 's/.*[Ee][Pp] *\([0-9][0-9]*\).*/\1/p'); [ -z "$n" ] && continue
  W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$f"); H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$f")
  if [ "$H" -ge 1900 ]; then TW=1080; TH=1920; TB=12000k; else TW=$((W/2*2)); TH=$((H/2*2)); TB=9000k; fi
  o=hls/$P/ep$n; mkdir -p $o
  ffmpeg -v error -y -i "$f" -filter_complex "[0:v]fps=24,split=3[a][b][c];[a]scale=$TW:$TH:flags=lanczos[v0];[b]scale=540:960:flags=lanczos[v1];[c]scale=360:640:flags=lanczos[v2]" \
    -map "[v0]" -map 0:a:0 -map "[v1]" -map 0:a:0 -map "[v2]" -map 0:a:0 \
    -c:v libx264 -preset slow -profile:v high -pix_fmt yuv420p -g 48 -keyint_min 48 -sc_threshold 0 \
    -crf:v:0 16 -maxrate:v:0 $TB -bufsize:v:0 18000k \
    -crf:v:1 20 -maxrate:v:1 2800k -bufsize:v:1 5600k \
    -crf:v:2 22 -maxrate:v:2 1100k -bufsize:v:2 2200k \
    -c:a aac -ar 48000 -b:a:0 256k -b:a:1 128k -b:a:2 96k \
    -f hls -hls_time 4 -hls_playlist_type vod -hls_flags independent_segments \
    -hls_segment_filename "$o/v%v/s%03d.ts" -master_pl_name master.m3u8 \
    -var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2" "$o/v%v/index.m3u8" || { echo "ep$n ENCODE FAILED" >> report.txt; continue; }
  echo "ep$n ${W}x${H} -> top ${TW}x${TH}  $(du -sm $o | cut -f1) MB" >> report.txt
  if [ "$n" -ge "$FROM" ]; then
    t=3.667
    ffmpeg -v error -y -ss $t -t 12 -i "$f" -vf "scale=720:1280:flags=lanczos,fps=24" -an -c:v libx264 -preset veryfast -crf 24 -maxrate 2500k -bufsize 5000k -movflags +faststart -pix_fmt yuv420p previews/$P-ep$n.mp4
    ffmpeg -v error -y -ss 5 -i "$f" -frames:v 1 -vf scale=360:640 previews/$P-ep$n-check.jpg
  fi
done
E="--endpoint-url $R2 --only-show-errors"
aws s3 sync hls/ s3://pinkmoon/ $E --exclude "*" --include "*.ts" --content-type video/mp2t --cache-control "public, max-age=31536000, immutable"
aws s3 sync hls/ s3://pinkmoon/ $E --exclude "*" --include "*.m3u8" --content-type application/vnd.apple.mpegurl --cache-control "public, max-age=600"
echo "== uploaded" >> report.txt
aws s3 ls s3://pinkmoon/$P/ $E --recursive --summarize | tail -2 >> report.txt
git add -f previews
cat report.txt

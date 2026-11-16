#!/bin/bash
# probe mode: report every file's size and streams, and test R2 access
MODE=$(jq -r .mode job.json)
{
echo "MODE $MODE"
find /tmp/src -type f | sort | while read -r f; do
  echo "== $(basename "$f")  $(du -m "$f" | cut -f1) MB"
  ffprobe -v error -show_entries format=duration,bit_rate:stream=codec_name,profile,width,height,r_frame_rate,bit_rate,pix_fmt,channels,sample_rate -of compact "$f" 2>&1 | head -6
done
echo "== R2 test"
echo ok > /tmp/t.txt
aws s3 cp /tmp/t.txt s3://pinkmoon/_test.txt --endpoint-url "$R2" 2>&1 | tail -1
aws s3 ls s3://pinkmoon/ --endpoint-url "$R2" 2>&1 | head
aws s3 rm s3://pinkmoon/_test.txt --endpoint-url "$R2" 2>&1 | tail -1
} > report.txt 2>&1
cat report.txt

# For the most recent file
tail -15 *(.om[1])

# For the 5 most recent files
for file in *(.om[1,5]); do
    echo "=== Last 15 lines of $file ==="
    tail -15 "$file"
    echo
done
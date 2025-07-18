for i in $(seq 1 50); do
    bash blockbuster_plot.sh --sfs sfss/sfs_${i}.blk -p sfss/prediction/test${i} -L 10000 -m 0.00001
done
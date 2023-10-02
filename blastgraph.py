from src.blast_to_graph import blast_to_graph
import subprocess
import os
import sys
import argparse
import multiprocessing

def main(arguments):

	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--file", help="FASTA file", required=True)
	parser.add_argument("-d", "--db", help="BLAST database", required=True)
	parser.add_argument("-e", "--evalue", help="BLAST E-value (default: 1e-80)", default="1e-80")
	parser.add_argument("-t", "--threads", help="Number of threads (default: 0, or all threads)", default=0, type=int)
	parser.add_argument("--force", help="Overwrites all files", action="store_true")
	args = parser.parse_args(arguments)	# Get args as args.name

	fasta_file = args.file
	db =  args.db
	evalue = args.evalue
	threads = int(args.threads)

	max_cores = multiprocessing.cpu_count()
	if threads <= 0 or threads > max_cores:
		threads = max_cores

	prefix = fasta_file.replace("." + fasta_file.split(".")[-1], "")

	blast_file = prefix + ".tsv"
	graph_file = prefix + ".pickle"

	BLAST_COLUMNS = "qacc sacc bitscore evalue sscinames"

	if not os.path.exists(blast_file) or args.force:
		print("Running BLAST...")
		subprocess.run('blastn -query {query} -db {db} -out {out} -evalue {evalue} -max_hsps 1 -outfmt "6 {cols}" -num_threads {threads}'.format(query=fasta_file, db=db, evalue=evalue, out=blast_file, cols=BLAST_COLUMNS, threads=threads), shell=True)
		subprocess.run('(echo "{cols}" && cat {file}) > {file}.tmp && mv {file}.tmp {file}'.format(cols=BLAST_COLUMNS.replace(" ", "\\t"), file=blast_file), shell=True)

	graph_df = blast_to_graph(blast_file, graph_file, "sscinames", "qacc", args.force)
	subprocess.run("python app.py {graph_file}".format(graph_file = graph_file), shell=True)

if __name__ == "__main__":
	main(sys.argv[1:])
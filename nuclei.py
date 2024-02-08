import os
import subprocess
import argparse
import sys

def chunk_file(filename, chunk_size):
    with open(filename, 'r') as f:
        lines = f.readlines()

    for i in range(0, len(lines), chunk_size):
        yield lines[i:i + chunk_size]

def install_docker():
    commands = [
        "sudo apt-get update",
        "sudo apt-get install ca-certificates curl",
        "sudo install -m 0755 -d /etc/apt/keyrings",
        "sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
        "sudo chmod a+r /etc/apt/keyrings/docker.asc",
        "echo deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null",
        "sudo apt-get update",
        "sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        "sudo docker pull projectdiscovery/nuclei:latest"
    ]

    for cmd in commands:
        subprocess.run(["bash", "-c", cmd])

def run_nuclei():
    subprocess.run(["bash", "-c", f"sudo docker pull projectdiscovery/nuclei:latest"])
    args = parse_args()
    domain_file = args.list
    output_file_base = os.path.splitext(os.path.basename(args.output))[0]
    output_files = []
    template_arg = f"-t /root/nuclei-templates/{args.template}" if args.template else ""
    memory_arg = f"--memory={args.ram}m" if args.ram else "--memory=2000m"
    used_ram = args.ram if args.ram else "2000"

    print(f"Used RAM: {used_ram}")

    if not os.path.exists(os.path.dirname(args.output)):
        os.makedirs(os.path.dirname(args.output))

    for i, chunk in enumerate(chunk_file(domain_file, 25)):
        temp_domain_file = f"temp_domain_{i}.txt"
        with open(temp_domain_file, 'w') as temp_file:
            temp_file.writelines(chunk)

        output_file = f"{os.path.dirname(args.output)}/{output_file_base}_{i}.json"
        output_files.append(output_file)

        print(f"Processing chunk {i} of domains...")
        subprocess.run(["bash", "-c", f"docker run --rm {memory_arg} -v $(pwd):/data projectdiscovery/nuclei:latest -list /data/{temp_domain_file} -o /data/{output_file} -fr {template_arg}"])

        os.remove(temp_domain_file)

    with open(args.output, 'w') as outfile:
        for fname in output_files:
            with open(fname) as infile:
                outfile.write(infile.read())
            os.remove(fname)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-list', required=False, help='Path to the domain list file')
    parser.add_argument('-o', '--output', required=False, help='Path to the output file')
    parser.add_argument('-t', '--template', required=False, help='Nuclei template to use')
    parser.add_argument('-ram', required=False, help='RAM memory in megabytes for Docker')
    parser.add_argument('-install', action='store_true', help='Install Docker and Nuclei')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.install:
        install_docker()
    if args.list and args.output:
        run_nuclei()
    elif not args.install:
        print("Missing arguments. Use -list, -o and optionally -t and -ram to specify input, output files, Nuclei template, and RAM for Docker.")
        sys.exit(1)

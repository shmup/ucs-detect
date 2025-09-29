#!/usr/bin/env python3
"""automated terminal testing for ucs-detect"""

import subprocess
import tempfile
import yaml
import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime
import shutil

class TerminalTester:
    """automated terminal tester for ucs-detect"""

    def __init__(self, output_dir="test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
        self.available_terminals = {}

        # terminal configurations
        # each entry: (check_cmd, run_cmd_template, needs_display)
        self.terminal_configs = {
            'xterm': {
                'check': ['xterm', '-version'],
                'run': 'xterm -e "{cmd}"',
                'needs_display': True,
            },
            'konsole': {
                'check': ['konsole', '--version'],
                'run': 'konsole -e "{cmd}"',
                'needs_display': True,
            },
            'gnome-terminal': {
                'check': ['gnome-terminal', '--version'],
                'run': 'gnome-terminal -- bash -c "{cmd}; read"',
                'needs_display': True,
            },
            'kitty': {
                'check': ['kitty', '--version'],
                'run': 'kitty sh -c "{cmd}"',
                'needs_display': True,
            },
            'alacritty': {
                'check': ['alacritty', '--version'],
                'run': 'alacritty -e sh -c "{cmd}"',
                'needs_display': True,
            },
            'foot': {
                'check': ['foot', '--version'],
                'run': 'foot sh -c "{cmd}"',
                'needs_display': True,
            },
            'rxvt-unicode': {
                'check': ['urxvt', '-help'],
                'run': 'urxvt -e sh -c "{cmd}"',
                'needs_display': True,
            },
            'st': {
                'check': ['st', '-v'],
                'run': 'st -e sh -c "{cmd}"',
                'needs_display': True,
            },
            'wezterm': {
                'check': ['wezterm', '--version'],
                'run': 'wezterm start -- sh -c "{cmd}"',
                'needs_display': True,
            },
            # terminals that might work without display
            'tmux': {
                'check': ['tmux', '-V'],
                'run': 'tmux new-session -d -s test "{cmd}"',
                'needs_display': False,
            },
            'screen': {
                'check': ['screen', '--version'],
                'run': 'screen -d -m -S test sh -c "{cmd}"',
                'needs_display': False,
            },
        }

        self.detect_terminals()

    def detect_terminals(self):
        """detect which terminals are available"""
        print("Detecting available terminals...")
        for name, config in self.terminal_configs.items():
            try:
                result = subprocess.run(
                    config['check'],
                    capture_output=True,
                    timeout=2,
                    text=True
                )
                if result.returncode == 0 or 'version' in result.stdout.lower() or 'version' in result.stderr.lower():
                    self.available_terminals[name] = True
                    print(f"  ✓ {name} found")
                else:
                    self.available_terminals[name] = False
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
                self.available_terminals[name] = False

        if not any(self.available_terminals.values()):
            print("Warning: No terminals detected!")
        else:
            print(f"Found {sum(self.available_terminals.values())} terminal(s)")

    def test_terminal_docker(self, terminal_name):
        """test terminal using docker approach"""
        print(f"\nTesting {terminal_name} via Docker...")

        dockerfile_content = f"""
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# install python and git
RUN apt-get update && apt-get install -y \\
    python3 python3-pip git \\
    xvfb x11vnc \\
    && rm -rf /var/lib/apt/lists/*

# install specific terminal
RUN apt-get update && apt-get install -y {terminal_name} \\
    && rm -rf /var/lib/apt/lists/*

# copy and install ucs-detect
COPY . /app
WORKDIR /app
RUN pip3 install -e .

# run test with virtual display
CMD Xvfb :99 -screen 0 1024x768x24 & \\
    export DISPLAY=:99 && \\
    sleep 2 && \\
    {terminal_name} -e 'ucs-detect --save-yaml=/app/result.yaml --quick' & \\
    sleep 10 && \\
    cat /app/result.yaml
"""

        # create temporary dockerfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write(dockerfile_content)
            dockerfile_path = f.name

        try:
            # build docker image
            image_name = f"ucs-detect-test-{terminal_name}"
            build_cmd = [
                'docker', 'build',
                '-f', dockerfile_path,
                '-t', image_name,
                '.'
            ]
            print(f"  Building Docker image...")
            subprocess.run(build_cmd, check=True, capture_output=True)

            # run container
            run_cmd = [
                'docker', 'run',
                '--rm',
                '-v', f'{os.getcwd()}:/app',
                image_name
            ]
            print(f"  Running test...")
            result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=30)

            # parse yaml from output
            if result.returncode == 0:
                try:
                    # attempt to extract yaml from output
                    lines = result.stdout.split('\n')
                    yaml_start = None
                    for i, line in enumerate(lines):
                        if line.startswith('datetime:'):
                            yaml_start = i
                            break

                    if yaml_start is not None:
                        yaml_content = '\n'.join(lines[yaml_start:])
                        data = yaml.safe_load(yaml_content)
                        return data
                except:
                    print(f"  Failed to parse YAML output")
                    return None
            else:
                print(f"  Docker run failed: {result.stderr}")
                return None

        finally:
            os.unlink(dockerfile_path)

    def test_terminal_native(self, terminal_name):
        """test terminal using native approach (requires display)"""
        if not self.available_terminals.get(terminal_name):
            print(f"  {terminal_name} not available")
            return None

        config = self.terminal_configs[terminal_name]

        # check display requirement
        if config['needs_display'] and not os.environ.get('DISPLAY'):
            print(f"  {terminal_name} requires DISPLAY but none set")
            return None

        print(f"\nTesting {terminal_name} natively...")

        # create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            output_file = f.name

        try:
            # build command
            ucs_cmd = f"ucs-detect --save-yaml={output_file} --quick"

            if terminal_name == 'tmux':
                # special handling for tmux
                session_name = f"ucs-test-{int(time.time())}"
                subprocess.run(['tmux', 'new-session', '-d', '-s', session_name, ucs_cmd])
                time.sleep(5)  # wait for completion
                subprocess.run(['tmux', 'kill-session', '-t', session_name])
            elif terminal_name == 'screen':
                # special handling for screen
                session_name = f"ucs-test-{int(time.time())}"
                subprocess.run(['screen', '-d', '-m', '-S', session_name, 'sh', '-c', ucs_cmd])
                time.sleep(5)  # wait for completion
                subprocess.run(['screen', '-X', '-S', session_name, 'quit'])
            else:
                # gui terminals
                full_cmd = config['run'].format(cmd=ucs_cmd)
                subprocess.run(full_cmd, shell=True, timeout=10)

            # read results
            if os.path.exists(output_file):
                with open(output_file) as f:
                    data = yaml.safe_load(f)
                return data
            else:
                print(f"  No output file generated")
                return None

        except subprocess.TimeoutExpired:
            print(f"  Test timed out")
            return None
        except Exception as e:
            print(f"  Error: {e}")
            return None
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_with_xvfb(self, terminal_name):
        """test terminal using xvfb virtual display"""
        if not shutil.which('xvfb-run'):
            print("  xvfb-run not available")
            return None

        if not self.available_terminals.get(terminal_name):
            print(f"  {terminal_name} not available")
            return None

        config = self.terminal_configs[terminal_name]
        print(f"\nTesting {terminal_name} with Xvfb...")

        # create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            output_file = f.name

        try:
            # build command
            ucs_cmd = f"ucs-detect --save-yaml={output_file} --quick"
            terminal_cmd = config['run'].format(cmd=ucs_cmd)

            # run with xvfb
            xvfb_cmd = ['xvfb-run', '-a', '--server-args=-screen 0 1024x768x24', 'sh', '-c', terminal_cmd]
            subprocess.run(xvfb_cmd, timeout=15)

            # read results
            if os.path.exists(output_file):
                with open(output_file) as f:
                    data = yaml.safe_load(f)
                return data
            else:
                print(f"  No output file generated")
                return None

        except subprocess.TimeoutExpired:
            print(f"  Test timed out")
            return None
        except Exception as e:
            print(f"  Error: {e}")
            return None
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def run_tests(self, terminals=None, method='auto'):
        """run tests on specified terminals

        Args:
            terminals: list of terminal names or None for all available
            method: 'docker', 'native', 'xvfb', or 'auto'
        """
        if terminals is None:
            terminals = [t for t, avail in self.available_terminals.items() if avail]

        print(f"\n{'='*60}")
        print(f"Testing {len(terminals)} terminal(s) using method: {method}")
        print(f"{'='*60}")

        for terminal in terminals:
            if method == 'docker':
                result = self.test_terminal_docker(terminal)
            elif method == 'native':
                result = self.test_terminal_native(terminal)
            elif method == 'xvfb':
                result = self.test_with_xvfb(terminal)
            else:  # auto
                # try methods in order of preference
                result = None
                if not self.terminal_configs[terminal]['needs_display']:
                    result = self.test_terminal_native(terminal)
                if result is None and shutil.which('xvfb-run'):
                    result = self.test_with_xvfb(terminal)
                if result is None and shutil.which('docker'):
                    result = self.test_terminal_docker(terminal)
                if result is None:
                    result = self.test_terminal_native(terminal)

            if result:
                self.results[terminal] = result
                self.save_result(terminal, result)
                print(f"  ✓ {terminal} test completed")
            else:
                print(f"  ✗ {terminal} test failed")

    def save_result(self, terminal_name, data):
        """save individual test result"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{terminal_name}_{timestamp}.yaml"
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

        print(f"  Saved: {filepath}")

    def generate_report(self):
        """generate aggregate report from all results"""
        if not self.results:
            print("\nNo results to report")
            return

        print(f"\n{'='*60}")
        print("Test Results Summary")
        print(f"{'='*60}")

        report = {
            'test_date': datetime.now().isoformat(),
            'terminals_tested': list(self.results.keys()),
            'summary': {}
        }

        for terminal, data in self.results.items():
            if data and 'test_results' in data:
                results = data['test_results']
                summary = {
                    'unicode_version': data.get('unicode_version', 'unknown'),
                    'seconds_elapsed': data.get('seconds_elapsed', 0),
                }

                # count failures for each test type
                for test_type in ['emoji_vs16_results', 'emoji_zwj_results', 'wide_character_results']:
                    if test_type in results:
                        total_failures = 0
                        for version, version_data in results[test_type].items():
                            if 'failed_codepoints' in version_data:
                                total_failures += len(version_data['failed_codepoints'])
                        summary[test_type + '_failures'] = total_failures

                report['summary'][terminal] = summary

                print(f"\n{terminal}:")
                print(f"  Unicode Version: {summary['unicode_version']}")
                print(f"  Test Duration: {summary['seconds_elapsed']:.2f}s")
                for key, value in summary.items():
                    if key.endswith('_failures'):
                        print(f"  {key}: {value}")

        # save aggregate report
        report_file = self.output_dir / f"aggregate_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nAggregate report saved: {report_file}")

        # generate comparison matrix
        self.generate_comparison_matrix()

    def generate_comparison_matrix(self):
        """generate a comparison matrix of terminal capabilities"""
        if len(self.results) < 2:
            return

        print(f"\n{'='*60}")
        print("Terminal Comparison Matrix")
        print(f"{'='*60}")

        # extract common test points
        test_types = ['emoji_vs16_results', 'emoji_zwj_results', 'wide_character_results']

        for test_type in test_types:
            print(f"\n{test_type.replace('_', ' ').title()}:")
            print(f"{'Terminal':<20} {'Failures':<10} {'Pass Rate':<10}")
            print("-" * 40)

            for terminal, data in self.results.items():
                if data and 'test_results' in data and test_type in data['test_results']:
                    results = data['test_results'][test_type]
                    total_tests = 0
                    total_failures = 0

                    for version, version_data in results.items():
                        if 'failed_codepoints' in version_data:
                            failures = len(version_data['failed_codepoints'])
                            total_failures += failures
                            # estimate total tests (this is approximate)
                            if 'limit_codepoints' in data.get('session_arguments', {}):
                                total_tests = data['session_arguments']['limit_codepoints']
                            else:
                                total_tests = 1000  # default estimate

                    pass_rate = ((total_tests - total_failures) / total_tests * 100) if total_tests > 0 else 0
                    print(f"{terminal:<20} {total_failures:<10} {pass_rate:.1f}%")


def main():
    """main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Automated terminal testing for ucs-detect')
    parser.add_argument('--terminals', nargs='+', help='Specific terminals to test')
    parser.add_argument('--method', choices=['docker', 'native', 'xvfb', 'auto'],
                       default='auto', help='Testing method')
    parser.add_argument('--output-dir', default='test_results',
                       help='Output directory for results')
    parser.add_argument('--list-terminals', action='store_true',
                       help='List available terminals and exit')

    args = parser.parse_args()

    tester = TerminalTester(output_dir=args.output_dir)

    if args.list_terminals:
        print("\nConfigured terminals:")
        for name, available in tester.available_terminals.items():
            status = "✓ available" if available else "✗ not found"
            print(f"  {name:<20} {status}")
        return

    tester.run_tests(terminals=args.terminals, method=args.method)
    tester.generate_report()


if __name__ == '__main__':
    main()
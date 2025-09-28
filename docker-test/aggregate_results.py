#!/usr/bin/env python3
"""aggregate terminal test results"""

import yaml
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def load_results(results_dir="/results"):
    """load all yaml result files"""
    results_path = Path(results_dir)
    if not results_path.exists():
        print(f"Results directory {results_dir} does not exist")
        return {}

    results = {}
    for yaml_file in results_path.glob("*.yaml"):
        terminal_name = yaml_file.stem.rsplit('_', 2)[0]  # remove timestamp
        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
                results[terminal_name] = data
                print(f"Loaded results for {terminal_name}")
        except Exception as e:
            print(f"Error loading {yaml_file}: {e}")

    return results

def analyze_results(results):
    """analyze and compare test results"""
    analysis = {
        'timestamp': datetime.now().isoformat(),
        'terminals_tested': len(results),
        'terminal_list': list(results.keys()),
        'comparison': {},
        'summary': {}
    }

    # extract key metrics for comparison
    for terminal, data in results.items():
        if not data:
            continue

        terminal_summary = {
            'unicode_version': data.get('unicode_version', 'unknown'),
            'python_version': data.get('python_version', 'unknown'),
            'test_duration': data.get('seconds_elapsed', 0),
            'system': data.get('system', 'unknown'),
        }

        # count failures by test type
        if 'test_results' in data:
            test_results = data['test_results']

            # emoji vs16 failures
            vs16_failures = 0
            if 'emoji_vs16_results' in test_results:
                for version, vdata in test_results['emoji_vs16_results'].items():
                    if 'failed_codepoints' in vdata:
                        vs16_failures += len(vdata['failed_codepoints'])
            terminal_summary['emoji_vs16_failures'] = vs16_failures

            # emoji zwj failures
            zwj_failures = 0
            if 'emoji_zwj_results' in test_results:
                for version, vdata in test_results['emoji_zwj_results'].items():
                    if 'failed_zwj_sequences' in vdata:
                        zwj_failures += len(vdata['failed_zwj_sequences'])
            terminal_summary['emoji_zwj_failures'] = zwj_failures

            # wide character failures
            wide_failures = 0
            if 'wide_character_results' in test_results:
                for version, vdata in test_results['wide_character_results'].items():
                    if 'failed_codepoints' in vdata:
                        wide_failures += len(vdata['failed_codepoints'])
            terminal_summary['wide_character_failures'] = wide_failures

            # language rendering results
            if 'language_results' in test_results:
                lang_results = test_results['language_results']
                if lang_results:
                    terminal_summary['languages_tested'] = len(lang_results)
                    terminal_summary['language_errors'] = sum(
                        1 for lang_data in lang_results.values()
                        if lang_data.get('errors', 0) > 0
                    )
                else:
                    terminal_summary['languages_tested'] = 0
                    terminal_summary['language_errors'] = 0

        analysis['summary'][terminal] = terminal_summary

    # create comparison matrix
    test_types = ['emoji_vs16_failures', 'emoji_zwj_failures', 'wide_character_failures']
    for test_type in test_types:
        comparison = {}
        for terminal, summary in analysis['summary'].items():
            if test_type in summary:
                comparison[terminal] = summary[test_type]
        analysis['comparison'][test_type] = comparison

    return analysis

def calculate_success_percentage(n_errors, n_total):
    """calculate success percentage from errors and total"""
    return ((n_total - n_errors) / n_total if n_total else 0) * 100

def percentage_to_grade(percentage):
    """convert success percentage to letter grade"""
    if percentage >= 95: return "A+"
    elif percentage >= 90: return "A"
    elif percentage >= 85: return "A-"
    elif percentage >= 80: return "B+"
    elif percentage >= 75: return "B"
    elif percentage >= 70: return "B-"
    elif percentage >= 65: return "C+"
    elif percentage >= 60: return "C"
    elif percentage >= 55: return "C-"
    elif percentage >= 50: return "D+"
    elif percentage >= 45: return "D"
    elif percentage >= 40: return "D-"
    else: return "F"

def calculate_terminal_scores(results):
    """calculate letter grades for each terminal"""
    scores = {}

    for terminal, data in results.items():
        if not data or 'test_results' not in data:
            continue

        test_results = data['test_results']
        terminal_scores = {}

        # WIDE score - wide character support
        wide_errors = 0
        wide_total = 0
        if 'unicode_wide_results' in test_results:
            for version, vdata in test_results['unicode_wide_results'].items():
                if 'n_errors' in vdata and 'n_total' in vdata:
                    wide_errors += vdata['n_errors']
                    wide_total += vdata['n_total']

        wide_pct = calculate_success_percentage(wide_errors, wide_total)
        terminal_scores['WIDE'] = {
            'percentage': wide_pct,
            'grade': percentage_to_grade(wide_pct),
            'errors': wide_errors,
            'total': wide_total
        }

        # VS16 score - variation selector-16 emoji
        vs16_errors = 0
        vs16_total = 0
        if 'emoji_vs16_results' in test_results:
            for version, vdata in test_results['emoji_vs16_results'].items():
                if 'n_errors' in vdata and 'n_total' in vdata:
                    vs16_errors += vdata['n_errors']
                    vs16_total += vdata['n_total']

        vs16_pct = calculate_success_percentage(vs16_errors, vs16_total)
        terminal_scores['VS16'] = {
            'percentage': vs16_pct,
            'grade': percentage_to_grade(vs16_pct),
            'errors': vs16_errors,
            'total': vs16_total
        }

        # ZWJ score - zero-width joiner emoji sequences
        zwj_errors = 0
        zwj_total = 0
        if 'emoji_zwj_results' in test_results:
            for version, vdata in test_results['emoji_zwj_results'].items():
                if 'n_errors' in vdata and 'n_total' in vdata:
                    zwj_errors += vdata['n_errors']
                    zwj_total += vdata['n_total']

        zwj_pct = calculate_success_percentage(zwj_errors, zwj_total)
        terminal_scores['ZWJ'] = {
            'percentage': zwj_pct,
            'grade': percentage_to_grade(zwj_pct),
            'errors': zwj_errors,
            'total': zwj_total
        }

        # LANG score - language rendering
        lang_errors = 0
        lang_total = 0
        if 'language_results' in test_results and test_results['language_results']:
            for lang_data in test_results['language_results'].values():
                if 'errors' in lang_data and 'n_total' in lang_data:
                    lang_errors += lang_data['errors']
                    lang_total += lang_data['n_total']

        lang_pct = calculate_success_percentage(lang_errors, lang_total)
        terminal_scores['LANG'] = {
            'percentage': lang_pct,
            'grade': percentage_to_grade(lang_pct),
            'errors': lang_errors,
            'total': lang_total
        }

        # FINAL score - weighted average (equal weight for now)
        valid_scores = [score['percentage'] for score in terminal_scores.values() if score['total'] > 0]
        final_pct = sum(valid_scores) / len(valid_scores) if valid_scores else 0
        terminal_scores['FINAL'] = {
            'percentage': final_pct,
            'grade': percentage_to_grade(final_pct),
            'components': len(valid_scores)
        }

        scores[terminal] = terminal_scores

    return scores

def generate_report(analysis, output_file="aggregate_report.json"):
    """generate readable report from analysis"""
    print("\n" + "="*60)
    print("Terminal Test Results Summary")
    print("="*60)
    print(f"Tested {analysis['terminals_tested']} terminals")
    print(f"Timestamp: {analysis['timestamp']}")
    print(f"Terminals: {', '.join(analysis['terminal_list'])}")

    # print grade table like jquast's results
    if 'scores' in analysis:
        print("\n" + "-"*80)
        print("Terminal Unicode Support Grades")
        print("-"*80)

        # create table header
        print(f"{'Terminal':<20} {'FINAL':<8} {'WIDE':<8} {'LANG':<8} {'ZWJ':<8} {'VS16':<8}")
        print("-"*80)

        # sort terminals by final score (best first)
        sorted_terminals = []
        for terminal, scores in analysis['scores'].items():
            final_pct = scores.get('FINAL', {}).get('percentage', 0)
            sorted_terminals.append((terminal, final_pct))
        sorted_terminals.sort(key=lambda x: x[1], reverse=True)

        # print results for each terminal
        for terminal, _ in sorted_terminals:
            scores = analysis['scores'][terminal]
            final_grade = scores.get('FINAL', {}).get('grade', 'N/A')
            wide_grade = scores.get('WIDE', {}).get('grade', 'N/A')
            lang_grade = scores.get('LANG', {}).get('grade', 'N/A')
            zwj_grade = scores.get('ZWJ', {}).get('grade', 'N/A')
            vs16_grade = scores.get('VS16', {}).get('grade', 'N/A')

            print(f"{terminal:<20} {final_grade:<8} {wide_grade:<8} {lang_grade:<8} {zwj_grade:<8} {vs16_grade:<8}")

        # print detailed percentages
        print("\n" + "-"*80)
        print("Detailed Percentages")
        print("-"*80)
        print(f"{'Terminal':<20} {'FINAL':<10} {'WIDE':<10} {'LANG':<10} {'ZWJ':<10} {'VS16':<10}")
        print("-"*80)

        for terminal, _ in sorted_terminals:
            scores = analysis['scores'][terminal]
            final_pct = scores.get('FINAL', {}).get('percentage', 0)
            wide_pct = scores.get('WIDE', {}).get('percentage', 0)
            lang_pct = scores.get('LANG', {}).get('percentage', 0)
            zwj_pct = scores.get('ZWJ', {}).get('percentage', 0)
            vs16_pct = scores.get('VS16', {}).get('percentage', 0)

            print(f"{terminal:<20} {final_pct:>8.1f}% {wide_pct:>8.1f}% {lang_pct:>8.1f}% {zwj_pct:>8.1f}% {vs16_pct:>8.1f}%")

    else:
        # fallback to old format if no scores calculated
        print("\n" + "-"*60)
        print("Unicode Support Comparison (Failure Counts)")
        print("-"*60)

        print(f"{'Terminal':<20} {'VS16':<10} {'ZWJ':<10} {'Wide':<10} {'Total':<10}")
        print("-"*60)

        for terminal, summary in analysis['summary'].items():
            vs16 = summary.get('emoji_vs16_failures', 'N/A')
            zwj = summary.get('emoji_zwj_failures', 'N/A')
            wide = summary.get('wide_character_failures', 'N/A')

            total = 0
            if isinstance(vs16, int):
                total += vs16
            if isinstance(zwj, int):
                total += zwj
            if isinstance(wide, int):
                total += wide

            print(f"{terminal:<20} {str(vs16):<10} {str(zwj):<10} {str(wide):<10} {total:<10}")

    # identify best performing terminals
    print("\n" + "-"*60)
    print("Performance Rankings")
    print("-"*60)

    # rank by total failures
    rankings = []
    for terminal, summary in analysis['summary'].items():
        total_failures = (
            summary.get('emoji_vs16_failures', 0) +
            summary.get('emoji_zwj_failures', 0) +
            summary.get('wide_character_failures', 0)
        )
        rankings.append((terminal, total_failures))

    rankings.sort(key=lambda x: x[1])

    print("\nBest Unicode Support (fewest failures):")
    for i, (terminal, failures) in enumerate(rankings[:5], 1):
        print(f"  {i}. {terminal}: {failures} failures")

    # save json report
    output_path = Path(output_file)
    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"\nDetailed report saved to: {output_path}")

    return analysis

def generate_markdown_report(analysis, output_file="terminal_report.md"):
    """generate markdown report for documentation"""
    lines = []
    lines.append("# Terminal Unicode Support Test Results\n")
    lines.append(f"Generated: {analysis['timestamp']}\n")
    lines.append(f"Terminals Tested: {analysis['terminals_tested']}\n")

    # add grade table like jquast's if scores available
    if 'scores' in analysis:
        lines.append("\n## Unicode Support Grades\n")
        lines.append("| Terminal Software | FINAL score | WIDE score | LANG score | ZWJ score | VS16 score |\n")
        lines.append("|-------------------|-------------|------------|------------|-----------|------------|\n")

        # sort terminals by final score (best first)
        sorted_terminals = []
        for terminal, scores in analysis['scores'].items():
            final_pct = scores.get('FINAL', {}).get('percentage', 0)
            sorted_terminals.append((terminal, final_pct))
        sorted_terminals.sort(key=lambda x: x[1], reverse=True)

        for terminal, _ in sorted_terminals:
            scores = analysis['scores'][terminal]
            final_grade = scores.get('FINAL', {}).get('grade', 'N/A')
            wide_grade = scores.get('WIDE', {}).get('grade', 'N/A')
            lang_grade = scores.get('LANG', {}).get('grade', 'N/A')
            zwj_grade = scores.get('ZWJ', {}).get('grade', 'N/A')
            vs16_grade = scores.get('VS16', {}).get('grade', 'N/A')

            lines.append(f"| {terminal} | {final_grade} | {wide_grade} | {lang_grade} | {zwj_grade} | {vs16_grade} |\n")

        lines.append("\n## Detailed Percentages\n")
        lines.append("| Terminal Software | FINAL % | WIDE % | LANG % | ZWJ % | VS16 % |\n")
        lines.append("|-------------------|---------|--------|--------|-------|--------|\n")

        for terminal, _ in sorted_terminals:
            scores = analysis['scores'][terminal]
            final_pct = scores.get('FINAL', {}).get('percentage', 0)
            wide_pct = scores.get('WIDE', {}).get('percentage', 0)
            lang_pct = scores.get('LANG', {}).get('percentage', 0)
            zwj_pct = scores.get('ZWJ', {}).get('percentage', 0)
            vs16_pct = scores.get('VS16', {}).get('percentage', 0)

            lines.append(f"| {terminal} | {final_pct:.1f}% | {wide_pct:.1f}% | {lang_pct:.1f}% | {zwj_pct:.1f}% | {vs16_pct:.1f}% |\n")

    else:
        # fallback to failure counts if no scores
        lines.append("\n## Summary Table\n")
        lines.append("| Terminal | VS16 Failures | ZWJ Failures | Wide Failures | Total |\n")
        lines.append("|----------|---------------|--------------|---------------|-------|\n")

        for terminal, summary in analysis['summary'].items():
            vs16 = summary.get('emoji_vs16_failures', 'N/A')
            zwj = summary.get('emoji_zwj_failures', 'N/A')
            wide = summary.get('wide_character_failures', 'N/A')
            total = 0
            if isinstance(vs16, int):
                total += vs16
            if isinstance(zwj, int):
                total += zwj
            if isinstance(wide, int):
                total += wide

            lines.append(f"| {terminal} | {vs16} | {zwj} | {wide} | {total} |\n")

    lines.append("\n## Test Details\n")
    for terminal, summary in analysis['summary'].items():
        lines.append(f"\n### {terminal}\n")
        lines.append(f"- Unicode Version: {summary.get('unicode_version', 'unknown')}\n")
        lines.append(f"- Test Duration: {summary.get('test_duration', 0):.2f}s\n")
        lines.append(f"- System: {summary.get('system', 'unknown')}\n")

    # save markdown
    with open(output_file, 'w') as f:
        f.writelines(lines)
    print(f"Markdown report saved to: {output_file}")

def main():
    """main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Aggregate terminal test results')
    parser.add_argument('--results-dir', default='docker-test/results',
                       help='Directory containing test results')
    parser.add_argument('--output', default='reports/aggregate_report.json',
                       help='Output file for JSON report')
    parser.add_argument('--markdown', default='reports/terminal_report.md',
                       help='Output file for Markdown report')

    args = parser.parse_args()

    # ensure reports directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)

    # load results
    results = load_results(args.results_dir)
    if not results:
        print("No results found to aggregate")
        return 1

    # analyze
    analysis = analyze_results(results)

    # calculate scores
    scores = calculate_terminal_scores(results)
    analysis['scores'] = scores

    # generate reports
    generate_report(analysis, args.output)
    generate_markdown_report(analysis, args.markdown)

    return 0

if __name__ == '__main__':
    sys.exit(main())
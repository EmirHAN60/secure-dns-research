"""Build the illustrated manuscript and submission PDF from audited saved results."""
from __future__ import annotations
import argparse
import csv
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, Image


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def number(x, signed=False):
    return 'not estimable' if x is None else format(x, '+.1f' if signed else '.1f')


def find(rows, provider, mode, origins=None):
    return next(r for r in rows if r['provider']==provider and r.get('mode',r.get('comparison'))==mode and (origins is None or r['origins']==origins))


def interval(row):
    return f"{number(row['median_delta_ms'],True)} [{number(row['ci95_low_ms'],True)}, {number(row['ci95_high_ms'],True)}]"


def mode_name(mode):
    return {'udp':'UDP','doh_fresh':'DoH fresh','doh_warm':'DoH established','doh_reused':'DoH established'}[mode]


def check_summary(summary, label):
    if summary.get('warnings'):
        raise ValueError(f'{label}: unresolved analysis warnings')
    for audit in summary.get('validation',{}).values():
        if isinstance(audit,dict) and (audit.get('validation_errors') or audit.get('transport_mismatches')):
            raise ValueError(f'{label}: saved-data audit failed')
    if summary['counts']['lookup_measurements']!=1800 or summary['counts']['pages']!=360:
        raise ValueError(f'{label}: the manuscript expects the complete 1800/360 collection')


def make_tokens(root, original, repeat, refs, profile):
    env=load(root/'data/environment.json');renv=load(root/'data/replication-2026-11-19/environment.json')
    browser=load_jsonl(root/'data/page-environment.jsonl')[0]
    rbrowser=load_jsonl(root/'data/replication-2026-11-19/page-environment.jsonl')[0]
    D=lambda p,m:find(original['lookup_paired'],p,m)
    original_bad=sum(r['failed'] for r in original['lookup_summary']+original['page_summary'])
    repeat_bad=sum(r['failed'] for r in repeat['lookup_summary']+repeat['page_summary'])
    bibliography=[]
    for paragraph in (root/'docs/REFERENCES.md').read_text(encoding='utf-8').split('\n\n'):
        if re.search(r'\(\d{4}',paragraph) and ('https://doi.org/' in paragraph or 'https://www.w3.org/' in paragraph):
            bibliography.append(re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\2',paragraph.strip()))
    if len(bibliography)!=len(refs):raise ValueError('Structured and formatted bibliography counts differ')
    tokens={
        'IDENTITY':f"{profile['author_name']}\n\nStudent ID: {profile['student_id']}\n\n{profile['institution']}\n\n{profile['department']}\n\nArchitecture of Computers (CII3SE003CI), 2026/2027",
        'REPOSITORY_URL':profile['repository_url'],
        'ENVIRONMENT':f"The historical host ran Windows {env['release']} {env['arch']} on an {env['cpu_model'].strip()}, with {env['logical_cpus']} logical processors and {number(env['total_memory_gib'])} GiB RAM. Node.js versions were {env['node']} and {renv['node']}. Chrome versions were {browser['browser']} and {rbrowser['browser']}, with Playwright {browser['playwright']}.",
        'COMPLETENESS':f"The original and second sessions recorded {original_bad} and {repeat_bad} failed measured attempts, respectively. The 3,600 lookups and 720 navigations passed the saved-packet and transport audits.",
        'PRIMARY_LOOKUP_RESULTS':(
            "Median paired fresh-DoH differences on 15 and 19 November were "
            f"{number(D('cloudflare','doh_fresh')['median_delta_ms'],True)} and "
            f"{number(find(repeat['lookup_paired'],'cloudflare','doh_fresh')['median_delta_ms'],True)} ms for Cloudflare, and "
            f"{number(D('google','doh_fresh')['median_delta_ms'],True)} and "
            f"{number(find(repeat['lookup_paired'],'google','doh_fresh')['median_delta_ms'],True)} ms for Google."
        ),
        'REFERENCES':'\n\n'.join(bibliography),
    }
    tokens.update(load(root/'docs/literature_tokens.json'))
    tokens.update(browser_tokens(root))
    tokens.update(control_tokens(root))
    tokens.update(loopback_tokens(root))
    tokens.update(repeatability_tokens(root))
    tokens.update(session_tokens(root))
    tokens.update(additional_date_tokens(root))
    tokens.update(layout_tokens(root))
    return tokens


def browser_tokens(root):
    with (root/'results/browser_phases.csv').open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 16:
        raise ValueError('Expected all sixteen browser phase contrasts')
    fresh = [row for row in rows if row['treatment'] == 'doh_fresh']
    document = [float(row['document_delta_ms']) for row in fresh]
    post_one = [abs(float(row['after_document_delta_ms'])) for row in fresh if row['hostnames'] == '1']
    post_eight = [float(row['after_document_delta_ms']) for row in fresh if row['hostnames'] == '8']
    established_load = [float(row['load_delta_ms']) for row in rows if row['treatment'] == 'doh_reused']
    return {
        'BROWSER_PHASE_RESULTS': (
            f"Across dates, providers and layouts, fresh DoH added {number(min(document))} to "
            f"{number(max(document))} ms through document response end at the paired median. "
            f"The median change after response end stayed within {number(max(post_one))} ms of zero "
            f"for one hostname and ranged from {number(min(post_eight),True)} to "
            f"{number(max(post_eight),True)} ms for eight. Established DoH load differences "
            f"ranged from {number(min(established_load),True)} to {number(max(established_load),True)} ms."
        ),
        'BROWSER_CAPTION': (
            "Figure 4. Median paired differences by navigation phase for both dates. "
            "Fresh and ready designate the DoH session state and 1 and 8 identify the hostname counts. "
            "Each point uses thirty complete pairs. The total is calculated per pair before taking its median."
        ),
    }


def control_tokens(root):
    analysis = load(root/'results/control_analysis.json')
    control = analysis['control']
    if control['status'] != 'complete':
        raise ValueError('The follow-up must be complete before rendering the paper')
    env = load(root/'data/control-2026-11-20/environment.json')
    forecast = control['forecast_validation']
    if forecast['windows_evaluated'] != env['windows'] or not forecast['plan_precedes_all_evaluated_windows']:
        raise ValueError('The follow-up forecast does not cover all planned windows')

    providers = ('cloudflare', 'google')
    def estimate(provider, comparison, baseline, metric='elapsed_ms'):
        return next(row['pooled_median_ms'] for row in control['paired_contrasts']
                    if (row['provider'], row['comparison'], row['baseline'], row['metric'])
                    == (provider, comparison, baseline, metric))

    def signed(value):
        return f'{value:+.2f}'

    bind_ready = [
        next(row['median_ms'] for row in control['marginals']
             if (row['provider'], row['mode'], row['metric']) == (provider, 'udp_fresh', 'bind_ready_ms'))
        for provider in providers
    ]
    fresh_vs_bound = [estimate(p, 'udp_fresh', 'udp_bound') for p in providers]
    postbind = [estimate(p, 'udp_fresh', 'udp_bound', 'post_bind_query_ms') for p in providers]
    doh_fresh_udp = [estimate(p, 'doh_warm', 'udp_fresh') for p in providers]
    doh_bound_udp = [estimate(p, 'doh_warm', 'udp_bound') for p in providers]
    google_bound = [row['median_ms'] for row in control['windows']
                    if (row['provider'], row['comparison'], row['baseline'], row['metric'])
                    == ('google', 'doh_warm', 'udp_bound', 'elapsed_ms')]
    historical = {row['provider']: row for row in analysis['historical']['pooled_contrasts']
                  if row['comparison'] == 'doh_warm'}
    google = historical['google']
    cf = historical['cloudflare']
    swaps = {row['provider']: row for row in control['baseline_swap_summary']}
    history_low, history_high = google['conditional_fixed_window_interval_ms']
    matches = forecast['positive_sign_matches']
    total = forecast['windows_evaluated']
    observed = [row['observed_median_ms'] for row in forecast['observations']]
    table = [
        "Table 1. Socket-control median paired differences in milliseconds.",
        "",
        "| Provider | Fresh − bound UDP, whole call | Fresh − bound UDP, after bind | DoH − fresh UDP | DoH − bound UDP |",
        "|---|---:|---:|---:|---:|",
    ]
    for idx, provider in enumerate(providers):
        values = (fresh_vs_bound[idx], postbind[idx], doh_fresh_udp[idx], doh_bound_udp[idx])
        table.append(f"| {provider.title()} | " + " | ".join(map(signed, values)) + " |")
    return {
        'ABSTRACT_CONTROL': (
            f"Across {control['measured_attempts']:,} follow-up attempts, median fresh UDP setup was about "
            f"{max(bind_ready):.2f} ms. Prebound UDP reversed the Cloudflare comparison in "
            f"{swaps['cloudflare']['strict_sign_flip_count']} of {total} windows."
        ),
        'CONTROL_DESIGN': (
            f"On 20 November, {env['windows']} windows targeted {env['interval_seconds']} seconds between starts. "
            f"Each included {env['reps']} repetitions and priming across all treatments. "
            f"The host used Windows {env['release']} and Node.js {env['node']}."
        ),
        'CONTROL_RESULTS': (
            f"The follow-up recorded {control['measured_attempts']:,} measured attempts and "
            f"{control['failed_measured_attempts']} measured failures. The median interval from fresh UDP "
            f"call start through binding was {bind_ready[0]:.2f} ms for Cloudflare and {bind_ready[1]:.2f} ms for "
            "Google. Table 1 contrasts whole-call and post-bind UDP differences and gives each DoH "
            "comparison against its own UDP baseline."
        ),
        'CONTROL_TABLE': '\n'.join(table),
        'HISTORY_TRANSFER': (
            f"Google's six historical windows gave a pooled median of {signed(google['pooled_median_ms'])} ms "
            f"and a fixed-window 95% interval of [{signed(history_low)}, {signed(history_high)}] ms. "
            f"Window medians ranged from {signed(google['window_median_min_ms'])} "
            f"to {signed(google['window_median_max_ms'])} ms. Held-window prediction matched "
            f"{google['retrospective_leave_window_sign_agrees']}/"
            f"{google['retrospective_leave_window_checks']} Google signs and "
            f"{cf['retrospective_leave_window_sign_agrees']}/{cf['retrospective_leave_window_checks']} Cloudflare signs."
        ),
        'FOLLOWUP_TRANSFER': (
            f"On 20 November, the historical positive Google sign matched {matches}/{total} windows. "
            f"Google window medians ranged from {signed(min(observed))} to {signed(max(observed))} ms "
            f"against fresh UDP and {signed(min(google_bound))} to {signed(max(google_bound))} ms against prebound UDP. "
            f"Changing baselines reversed {swaps['cloudflare']['strict_sign_flip_count']} Cloudflare signs "
            f"and {swaps['google']['strict_sign_flip_count']} Google signs. The historical comparison crosses "
            "a Windows build change and the switch to explicit binding."
        ),
        'HISTORY_FIGURE': (
            "![Historical window effects and conditional intervals.](../figures/historical_window_sensitivity.png)\n\n"
            "Figure 2. Historical lookup contrasts for each sampled window. Pooled intervals describe "
            "conditional uncertainty within those windows."
        ),
        'CONTROL_INTERPRETATION': (
            f"Changing the UDP baseline shifted the 20 November established DoH median contrast by "
            f"{signed(doh_bound_udp[0] - doh_fresh_udp[0])} ms for Cloudflare and "
            f"{signed(doh_bound_udp[1] - doh_fresh_udp[1])} ms for Google. Post-bind differences can reflect "
            "source-port-dependent network handling as well as client scheduling and service behavior. "
            "Google's reversals persist with both resources prepared in advance."
        ),
    }


def loopback_tokens(root):
    result = load(root/'results/loopback_summary.json')
    return {
        'LOOPBACK_RESULTS': (
            f"In {result['complete_pairs']} complete loopback pairs, the fresh socket reached readiness "
            f"in {result['fresh_ready_median_ms']:.3f} ms at the median. Fresh minus prebound UDP "
            f"was {result['whole_paired_median_ms']:+.4f} ms over the whole call and "
            f"{result['query_paired_median_ms']:+.3f} ms over the ready query stage. "
            "This calibration uses a local process and cannot quantify the change in a public UDP route."
        )
    }


def extension_attempts(root, summary):
    return sum(load(root / item['directory'] / 'environment.json')['measured_rows']
               for item in summary['sessions'])


def session_tokens(root):
    summary = load(root/'results/session_extension/summary.json')
    sessions = summary['sessions']
    if len(sessions) != 3 or any(item['status'] != 'complete' for item in sessions):
        raise ValueError('The revised paper requires three completed, audited sessions')
    calibration = load(root/'data/control-2026-11-20/environment.json')
    for item in sessions:
        environment = load(root / item['directory'] / 'environment.json')
        if any(environment[key] != calibration[key] for key in ('release', 'node', 'openssl', 'arch')):
            raise ValueError('A held-out OS/runtime differs from calibration; revise the matched-build interpretation')
    starts = [datetime.fromisoformat(item['actual_start_utc']) for item in sessions]
    ends = [datetime.fromisoformat(item['actual_finish_utc']) for item in sessions]
    if starts != sorted(starts) or any(end > start for end, start in zip(ends, starts[1:])):
        raise ValueError('Held-out sessions must be chronological and nonoverlapping')
    warsaw_november = timezone(timedelta(hours=1))
    local_times = [stamp.astimezone(warsaw_november).strftime('%H:%M') for stamp in starts]
    calibration_start = datetime.fromisoformat(calibration['started_utc']).astimezone(
        warsaw_november
    ).strftime('%H:%M')
    span = (ends[-1] - starts[0]).total_seconds() / 60
    keys = ('provider', 'comparison', 'baseline', 'metric')
    ready = {
        provider: next(row for row in summary['prospective_summary']
                       if tuple(row[key] for key in keys) == (provider, 'doh_warm', 'udp_bound', 'elapsed_ms'))
        for provider in ('cloudflare', 'google')
    }
    google = ready['google']
    table = [
        'Table 3. Established DoH minus prebound UDP in the 22 November holdout.',
        '',
        '| Warsaw start | Provider | Pairs | Signed median ms | Median of absolute differences (ms) | Pairs beyond ±2 ms |',
        '|---|---|---:|---:|---:|---:|',
    ]
    for stamp, session in zip(local_times, sessions):
        identifier = session['session_id']
        for provider in ready:
            target = (provider, 'doh_warm', 'udp_bound', 'elapsed_ms')
            row = next(row for row in summary['session_effects']
                       if tuple(row[k] for k in keys) == target and row['session_id'] == identifier)
            rate = next(row for row in summary['thresholds']['paired_rates']
                        if tuple(row[k] for k in keys) == target and row.get('session_id') == identifier
                        and row['level'] == 'session' and row['threshold_ms'] == 2.0)
            if rate['complete_pairs'] != row['complete_pairs']:
                raise ValueError('Session threshold denominator differs from its paired sample')
            table.append(f"| {stamp} | {provider.title()} | {row['complete_pairs']} | {row['median_delta_ms']:+.2f} | "
                         f"{row['median_abs_delta_ms']:.2f} | {rate['fraction_abs_gt_threshold']:.0%} |")

    def describe(provider):
        row = ready[provider]
        category = next(item for item in row['threshold_category_scores'] if item['threshold_ms'] == 2.0)
        return (
            f"{provider.title()}'s fixed ready-state forecast of {row['forecast_point_ms']:+.2f} ms matched "
            f"{row['sign_matches']}/{row['session_count']} session signs and "
            f"{category['matches']}/{category['evaluated']} categories at ±2 ms. "
            f"Mean absolute error was {row['forecast_mae_ms']:.2f} ms against "
            f"{row['zero_adjustment_mae_ms']:.2f} ms for predicting zero."
        )

    failures = sum(item['audit']['failed_measured_attempts'] for item in sessions)
    failure_note = f"The sessions recorded {failures} measured failures."
    if failures == 1:
        failure_note = "One Google prebound UDP timeout in the second session left 299 complete pairs."
    return {
        'SESSION_ABSTRACT': (
            f"A 20 November calibration forecast was then held fixed for {extension_attempts(root, summary):,} "
            f"attempts across three 22 November evening sessions. Against prebound UDP, the forecast matched "
            f"{google['sign_matches']} of {google['session_count']} Google session signs."
        ),
        'SESSION_DESIGN': (
            f"The 20 November calibration started at {calibration_start} Warsaw time. On 22 November, "
            f"three held-out sessions started around {local_times[0]}, {local_times[1]} and "
            f"{local_times[2]} Warsaw time, covering {span:.0f} minutes from first start to last finish. "
            "Each ran three windows with the socket-control design. The operating-system release and runtime "
            "versions matched the calibration. The only collector code change was an up-front transaction ID "
            "budget check. The planned and actual times are retained."
        ),
        'SESSION_RESULTS': '\n\n'.join([
            describe('cloudflare') + ' ' + describe('google') + ' ' + failure_note,
            '\n'.join(table),
            "Note. The 2 ms band is one of four fixed sensitivity bands. The last two columns describe individual "
            "complete pairs, and the signed median summarizes direction. The companion tables report all four bands.",
        ]),
        'SESSION_FIGURE': (
            "![Window and session medians for the held-out controls.](../figures/session_effects.png)\n\n"
            "Figure 3. Held-out window and session medians against the two UDP baselines. "
            "The bands show illustrative effect sizes for lookup latency."
        ),
        'SESSION_LIMITS': (
            "The calibration and holdouts differ in date and time of day. Their differences cannot isolate either. "
            "Repeated morning and evening sessions on independently identified networks remain necessary "
            "for stronger temporal and network coverage."
        ),
        'SESSION_CONCLUSION': (
            "Fresh HTTPS setup was associated with longer historical lookup times. The loopback "
            "calibration timed the local socket-readiness stage. The public-resolver experiment quantified "
            "sensitivity to the UDP baseline and measured error when applying a frozen forecast to another day."
        ),
    }


def additional_date_tokens(root):
    check = load(root/'results/additional_date.json')
    rows = {row['provider']: row for row in check['comparisons'] if row['baseline'] == 'udp_bound'}
    cf, google = (rows[key] for key in ('cloudflare', 'google'))
    agreement = "matched" if google['sign_matches'] else "missed"
    threshold = next(row for row in google['thresholds'] if row['threshold_ms'] == 2.0)
    band = "matched" if threshold['category_matches'] else "missed"
    return {
        'DATE_ABSTRACT': (
            f"A separate 23 November session measured a Google median of {google['median_delta_ms']:+.2f} ms "
            "against the ready UDP baseline."
        ),
        'DATE_METHOD': (
            "A separate 23 November verification used the same design and frozen forecasts, with a new seed. "
            "Its plan was recorded after the first evening extension and before this run. It adds one held-out date."
        ),
        'DATE_RESULTS': (
            f"The 23 November check recorded {check['audit']['measured_attempts']:,} attempts and "
            f"{check['audit']['failed_measured_attempts']} failures. Against prebound UDP, the paired median was "
            f"{cf['median_delta_ms']:+.2f} ms for Cloudflare and {google['median_delta_ms']:+.2f} ms for Google. "
            f"The unchanged Google forecast {agreement} the sign and {band} the ±2 ms category. "
            f"Its absolute error was {google['forecast_absolute_error_ms']:.2f} ms, "
            f"compared with {google['zero_absolute_error_ms']:.2f} ms for predicting zero. "
            "These scores describe the additional date separately."
        ),
    }


def layout_tokens(root):
    result = load(root/'results/browser-layout-2026-11-22/summary.json')
    effects = {row['layout']: row for row in result['paired_effects']}
    parallel, sequential = (effects[key] for key in ('parallel', 'sequential'))
    conditions = result['design']['conditions']
    base = min(condition['requested_gate_ms'] for condition in conditions)
    extra = max(condition['requested_gate_ms'] for condition in conditions) - base
    interaction = result['interaction']
    gate_summary = load(root/'results/browser-layout-2026-11-22/gate_wait_summary.json')
    realized = gate_summary['by_condition']['sequential']
    union = gate_summary['median_paired_gate_union_delta_ms']
    return {
        'LAYOUT_ABSTRACT': (
            f"Raising each requested wait by {extra:.0f} ms yielded median paired completion increases of "
            f"{parallel['median_paired_delta_ms']:.0f} ms with parallel and "
            f"{sequential['median_paired_delta_ms']:.0f} ms with sequential requests."
        ),
        'LAYOUT_METHOD': (
            f"A separate randomized Chrome experiment used the same seven image payloads under two request "
            f"dependencies and gate waits of {base:.0f} and {base + extra:.0f} ms. Sequential code waited for each "
            "image load before requesting the next. Parallel code issued all requests before awaiting completion. "
            "The primary outcome was script start to verified image completion. Request and gate timestamps checked "
            "the intended dependencies. Injected delays model waiting at the gate, and this experiment uses local bytes."
        ),
        'LAYOUT_RESULTS': (
            f"Raising each requested gate wait from {base:.0f} to {base + extra:.0f} ms yielded a median paired change of "
            f"{parallel['median_paired_delta_ms']:+.1f} ms in the parallel layout and "
            f"{sequential['median_paired_delta_ms']:+.1f} ms in the sequential layout. "
            f"Across {interaction['complete_blocks']} complete randomized blocks, the median paired interaction "
            f"was {interaction['median_ms']:+.1f} ms. Counting overlapping waits once, the median paired increase "
            f"in time with a gate active was {union['parallel']:+.1f} ms and {union['sequential']:+.1f} ms, "
            f"respectively. The sequential median gate waits were "
            f"{realized['baseline']['median_gate_wait_ms']:.1f} and "
            f"{realized['added']['median_gate_wait_ms']:.1f} ms for the two requested waits."
        ),
    }


def repeatability_tokens(root):
    report = load(root/'results/repeatability/summary.json')
    completed = [run for run in report['runs'] if run['status'] == 'complete']
    identifiers = [run['run_id'] for run in completed]
    if not identifiers or identifiers[0] != 'A1':
        raise ValueError('No complete initial repeatability run')
    environments = [load(root/run['directory']/'environment.json') for run in completed]
    attempts = sum(env['measured_rows'] for env in environments)
    failed = sum(run['audit']['failed_measured_attempts'] for run in completed)
    context = (
        'On one host, A1 used home Wi-Fi, B1 used a phone hotspot by user report, '
        'and A2 returned to home Wi-Fi with matching recorded local route properties.'
        if identifiers == ['A1', 'B1', 'A2']
        else 'The same host used home Wi-Fi for A1 and a phone hotspot for B1, by user report.'
        if identifiers == ['A1', 'B1']
        else 'One run used the original host and connection.'
    )
    cet = timezone(timedelta(hours=1))
    times = [
        f"{run['run_id']} {datetime.fromisoformat(env['started_utc']).astimezone(cet).strftime('%d Nov %H:%M')}"
        for run, env in zip(completed, environments)
    ]
    chronology = f"Local starts were {', '.join(times)}."
    table = [
        'Table 2. Weighted median absolute difference (ms) and weighted share above 2 ms.',
        '',
        '| Run | Provider | UDP–UDP | DoH–DoH | DoH–UDP |',
        '|---|---|---:|---:|---:|',
    ]
    for run in completed:
        for provider in ('cloudflare', 'google'):
            classes = {row['pair_class']: row for row in report['primary_classes']
                       if row['run_id'] == run['run_id'] and row['provider'] == provider
                       and row['flow_condition'] == 'repeat_flow'}
            bands = next(row for row in report['threshold_comparisons']
                         if row['run_id'] == run['run_id'] and row['provider'] == provider
                         and row['flow_condition'] == 'repeat_flow' and row['threshold_ms'] == 2.0)
            cells = []
            for code in ('UU', 'DD', 'DU'):
                value = classes[code]['weighted_median_abs_delta_ms']
                rate = bands[f'{code.lower()}_fraction_abs_gt_threshold']
                cells.append(f'{value:.2f} / {rate:.0%}' if value is not None and rate is not None else 'Unavailable')
            table.append(f"| {run['run_id']} | {provider.title()} | " + " | ".join(cells) + " |")
    example = next(row for row in report['threshold_comparisons']
                   if row['run_id'] == 'A1' and row['provider'] == 'cloudflare'
                   and row['flow_condition'] == 'repeat_flow' and row['threshold_ms'] == 2.0)
    google_flows = {row['pair_class']: row['weighted_median_abs_delta_ms'] for row in report['primary_classes']
                    if row['run_id'] == 'A1' and row['provider'] == 'google'
                    and row['flow_condition'] == 'distinct_flows'}
    google_signed = {row['run_id']: row['weighted_median_signed_delta_ms'] for row in report['primary_classes']
                     if row['provider'] == 'google' and row['flow_condition'] == 'repeat_flow'
                     and row['pair_class'] == 'DU'}
    signed_by_run = ', '.join(
        f"{run} {number(google_signed[run], signed=True)} ms" for run in identifiers
    )
    return {
        'REPEATABILITY_ABSTRACT': (
            f"Across {attempts:,} repeatability attempts, we compared same-mode and cross-mode differences at "
            "matched start intervals. In the initial Cloudflare run the weighted shares beyond 2 ms were "
            f"{example['uu_fraction_abs_gt_threshold']:.0%} for UDP repeats, "
            f"{example['dd_fraction_abs_gt_threshold']:.0%} for DoH repeats and "
            f"{example['du_fraction_abs_gt_threshold']:.0%} across modes."
        ),
        'REPEATABILITY_METHOD': (
            "Each run interleaved two UDP and two DoH queries per block. All six protocol orders were used "
            "for same-flow repeats and repeats on distinct prepared flows. Each provider had two sockets and "
            "two HTTP/2 sessions per window. Three windows yielded 2,880 measured attempts per run. "
            "The primary analysis matches adjacent positions with 75–125 ms between actual starts across "
            "randomized orders. We weight windows and common cells equally. "
            + context + " " + chronology
        ),
        'REPEATABILITY_RESULTS': '\n\n'.join([
            '\n'.join(table),
            "Note. Same-protocol pairs in this table used the same prepared flow within each mode. "
            "Weights are shared across observed position and domain cells. The companion files retain counts, "
            "other thresholds, distinct-flow results and start-interval sensitivity.",
            "![Observed DoH repeat and cross-mode magnitudes by flow condition.](../figures/repeatability_fixed_flow_comparison.png)",
            "Figure 1. Weighted median absolute differences for repeated DoH (DD) and cross-mode "
            "pairs (DU). Flow conditions refer to how blocks assign the two requests per protocol. "
            "Each estimate uses its condition's common cells.",
            f"The runs recorded {attempts:,} measured attempts, including {failed} unsuccessful "
            f"{'attempt' if failed == 1 else 'attempts'}.",
            f"Google's weighted signed DoH-minus-UDP medians in repeat-flow blocks were {signed_by_run}.",
            f"With distinct prepared flows in A1, Google's median absolute DoH repeat difference was "
            f"{google_flows['DD']:.2f} ms and the comparable cross-mode difference was {google_flows['DU']:.2f} ms. "
            "Using distinct flows leaves substantial same-protocol variation in this run.",
        ]),
    }


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def extended_results(root, original, repeat):
    lines=['# Historical results and figure guide','',
           'These tables describe the 15 and 19 November collections. Positive paired differences indicate slower DoH. Failures remain in attempt counts and successful-latency estimates condition on success.','',
           'See [the follow-up socket control and prediction results](CONTROL_RESULTS.md) and [the browser phase analysis](BROWSER_PHASES.md) for the revised paper.','',
           '| Date | Measured lookup attempts | Page attempts | Lookup priming records | Failed measured attempts |',
           '|---|---:|---:|---:|---:|']
    for date,s in [('2026-11-15',original),('2026-11-19',repeat)]:
        lines.append(f"| {date} | {s['counts']['lookup_measurements']} | {s['counts']['pages']} | {s['counts']['lookup_phase_counts']['prime']} | {sum(r['failed'] for r in s['lookup_summary']+s['page_summary'])} |")
    for date,s,folder in [('2026-11-15',original,'results'),('2026-11-19',repeat,'results/replication-2026-11-19')]:
        lines.extend(['',f'## Session {date}','','### Lookup distributions','',
                      '| Provider | Mode | Success / attempts | Median ms | IQR ms | p95 ms | Paired difference ms [95% interval] |',
                      '|---|---|---:|---:|---:|---:|---|'])
        for p in ['cloudflare','google']:
            for m in ['udp','doh_fresh','doh_warm']:
                r=find(s['lookup_summary'],p,m);effect='Baseline' if m=='udp' else interval(find(s['lookup_paired'],p,m))
                lines.append(f"| {p.title()} | {mode_name(m)} | {r['succeeded']}/{r['attempted']} | {number(r['median_ms'])} | {number(r['iqr_ms'])} | {number(r['p95_ms'])} | {effect} |")
        lines.extend(['','### Controlled page load distributions','',
                      '| Provider | Hostnames | Mode | Success / attempts | Median ms | p95 ms | Paired difference ms [95% interval] |',
                      '|---|---:|---|---:|---:|---:|---|'])
        for p in ['cloudflare','google']:
            for origins in [1,8]:
                for m in ['udp','doh_fresh','doh_reused']:
                    r=find(s['page_summary'],p,m,origins);effect='Baseline' if m=='udp' else interval(find(s['page_paired'],p,m,origins))
                    lines.append(f"| {p.title()} | {origins} | {mode_name(m)} | {r['succeeded']}/{r['attempted']} | {number(r['median_ms'])} | {number(r['p95_ms'])} | {effect} |")
        lines.extend(['','### Established lookup contrasts by window','',
                      '| Provider | Window | Matched pairs | Median paired difference ms |', '|---|---:|---:|---:|'])
        for r in s['window_effects']:
            if r['experiment']=='lookup' and r['comparison']=='doh_warm':lines.append(f"| {r['provider'].title()} | {r['window']} | {r['complete_pairs']} | {number(r['median_delta_ms'],True)} |")
        rb=load(root/folder/'robustness.json')
        lines.extend(['','### Dependence and sign sensitivity','',
                      '| Provider | Lookup contrast | Domain-cluster interval ms | Positive paired fraction | Window sign reversal |',
                      '|---|---|---|---:|---|'])
        for r in rb['comparisons']:
            if r['experiment']=='lookup':lines.append(f"| {r['provider'].title()} | {mode_name(r['comparison'])} | [{number(r['domain_cluster_ci95_low_ms'],True)}, {number(r['domain_cluster_ci95_high_ms'],True)}] | {100*r['positive_fraction']:.1f}% | {r['window_sign_reversal']} |")
        lines.extend(['','The cluster interval resamples ten observed hostname clusters. It is a secondary conditional sensitivity, not a solution to temporal dependence. Sign fractions describe matched samples and are not hypothesis-test p-values. All values are retained without trimming.','',
                      f'[Full primary summary](../{folder}/summary.json) · [Window effects](../{folder}/window_effects.csv) · [Leave-one-window-out](../{folder}/leave_one_window_out.csv) · [Domain effects](../{folder}/domain_effects.csv) · [Robustness details](../{folder}/robustness.json)'])
    lines.extend(['','## Figure guide',''])
    manifest=load(root/'figures/all_figures.json')
    for fig in manifest['figures']:
        # Both plot implementations expose the exported relative files in the manifest.
        name=fig.get('name',fig.get('stem',fig.get('title','Figure')))
        caption=fig.get('caption','')
        label=fig.get('date',fig.get('dataset',''))
        directory='../figures/' if fig.get('dataset') in ['original','cross-date','cross_date','comparison'] or fig.get('stem')=='cross_date_comparison' else '../figures/'+fig.get('dataset','')+'/'
        lines.extend([f'### {name} {label}','',caption,'',f"![{name} {label}]({directory}{name}.png)",'',f'[Vector PDF]({directory}{name}.pdf) · [SVG]({directory}{name}.svg)',''])
    lines.extend(['','## Reading the evidence','','The within-window and per-domain intervals condition on the observed time periods. Google established DoH changes sign within both historical dates. The [held-window analysis](CONTROL_RESULTS.md) measures how often the pooled sign transfers.','',
                  'The browser fixture uses live DNS waiting and fixed local content. Runtime versions differ across dates. See [methods](METHODS.md) and [reproduction details](REPRODUCIBILITY.md).',''])
    (root/'docs/RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')


def inline(text):
    text=html.escape(text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'\*([^*]+)\*',r'<i>\1</i>',text)
    text=re.sub(r'`([^`]+)`',r'\1',text)
    def link(match):
        url=match[1];suffix=''
        while url and url[-1] in '.,;':suffix=url[-1]+suffix;url=url[:-1]
        return f'<link href="{url}" color="#183d5a">{url}</link>'+suffix
    text=re.sub(r'(https://[^\s<]+)',link,text)
    return text


def fonts():
    folder = Path('C:/Windows/Fonts')
    filenames = ('times.ttf', 'timesbd.ttf', 'timesi.ttf', 'timesbi.ttf')
    if not all((folder / name).is_file() for name in filenames):
        from matplotlib import get_data_path

        folder = Path(get_data_path()) / 'fonts/ttf'
        filenames = ('DejaVuSerif.ttf', 'DejaVuSerif-Bold.ttf',
                     'DejaVuSerif-Italic.ttf', 'DejaVuSerif-BoldItalic.ttf')
    names = ('Paper', 'PaperBold', 'PaperItalic', 'PaperBoldItalic')
    for name, filename in zip(names, filenames):
        pdfmetrics.registerFont(TTFont(name, str(folder / filename)))
    pdfmetrics.registerFontFamily('Paper', normal=names[0], bold=names[1], italic=names[2], boldItalic=names[3])
    return names[:2]


def render_pdf(markdown, root, profile):
    font,bold=fonts()
    body=ParagraphStyle('Body',fontName=font,fontSize=12,leading=24,firstLineIndent=36,allowWidows=0,allowOrphans=0)
    plain=ParagraphStyle('Plain',parent=body,firstLineIndent=0)
    heading=ParagraphStyle('Heading',fontName=bold,fontSize=12,leading=24,alignment=TA_CENTER,spaceBefore=10,keepWithNext=True)
    sub=ParagraphStyle('Subheading',parent=heading,alignment=0)
    title=ParagraphStyle('Title',parent=heading,fontSize=14,leading=20,spaceAfter=8)
    identity=ParagraphStyle('Identity',parent=plain,alignment=TA_CENTER,leading=20,spaceAfter=4)
    caption=ParagraphStyle('Caption',fontName=font,fontSize=10.5,leading=14,spaceBefore=5,spaceAfter=8)
    tablecap=ParagraphStyle('TableCaption',parent=caption,keepWithNext=True)
    cell=ParagraphStyle('Cell',fontName=font,fontSize=9.1,leading=12)
    cellhead=ParagraphStyle('CellHead',parent=cell,fontName=bold)
    reference=ParagraphStyle('Reference',parent=body,leftIndent=36,firstLineIndent=-36,spaceAfter=6)
    blocks=markdown.split('\n\n');story=[];abstract=False;refs=False;index=0
    while index<len(blocks):
        block=blocks[index].strip();index+=1
        if not block:continue
        if block.startswith('# '):story.append(Paragraph(inline(block[2:]),title));continue
        if block.startswith('## '):
            name=block[3:];abstract=False
            if name=='References':refs=True;story.append(PageBreak())
            story.append(Paragraph(inline(name),heading));continue
        if block.startswith('### '):
            name=block[4:];abstract=name=='Abstract'
            if abstract:story.append(PageBreak())
            story.append(Paragraph(inline(name),heading if abstract else sub));continue
        image=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',block)
        if image:
            path=(root/image[2]).resolve()
            if not path.is_file() or not path.is_relative_to(root):raise ValueError('Missing or external figure '+str(path))
            picture=Image(str(path));ratio=picture.imageHeight/picture.imageWidth;picture.drawWidth=468;picture.drawHeight=468*ratio
            if picture.drawHeight>330:picture.drawHeight=330;picture.drawWidth=330/ratio
            group=[picture]
            if index<len(blocks) and blocks[index].strip().startswith('Figure '):group.append(Paragraph(inline(blocks[index].strip()),caption));index+=1
            story.extend([Spacer(1,8),KeepTogether(group),Spacer(1,8)]);continue
        if block.startswith('|'):
            rows=[[c.strip() for c in line.strip().strip('|').split('|')] for line in block.splitlines() if line.strip() and not re.fullmatch(r'[| :\-]+',line.strip())]
            count = len(rows[0])
            if rows[0][0] == 'Warsaw start':
                widths = [62, 62, 46, 86, 112, 100]
            elif count == 6:
                widths = [60, 88, 58, 45, 42, 175]
            else:
                widths = [468 / count] * count
            formatted=[[Paragraph(inline(c),cellhead if i==0 else cell) for c in row] for i,row in enumerate(rows)]
            table=Table(formatted,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('LINEABOVE',(0,0),(-1,0),0.7,colors.black),('LINEBELOW',(0,0),(-1,0),0.5,colors.black),('LINEBELOW',(0,-1),(-1,-1),0.7,colors.black),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f3f3')])]))
            story.append(table);continue
        if block.startswith('Table '):story.append(Paragraph('<b>'+inline(block)+'</b>',tablecap));continue
        if block.startswith('Note.'):story.append(Paragraph(inline(block),caption));continue
        if block.startswith('Keywords:'):story.append(Paragraph('<i>Keywords:</i>'+inline(block[len('Keywords:'):]),plain));story.append(PageBreak());abstract=False;continue
        if block in [profile['author_name'],f"Student ID: {profile['student_id']}",profile['institution'],profile['department'],'Architecture of Computers (CII3SE003CI), 2026/2027']:story.append(Paragraph(inline(block),identity));continue
        paragraph = Paragraph(inline(block),reference if refs else plain if abstract else body)
        story.append(KeepTogether([paragraph]) if refs else paragraph)
    output=root/'Secure_DNS_Research_Paper.pdf'
    def page_number(canvas,doc):
        canvas.saveState();canvas.setFont(font,12);canvas.drawRightString(540,756,str(doc.page));canvas.restoreState()
    document=SimpleDocTemplate(str(output),pagesize=letter,leftMargin=72,rightMargin=72,topMargin=72,title='DNS over HTTPS versus UDP: Lookup Latency and Controlled Browser Loads',bottomMargin=72,author=profile['author_name'],subject='UDP socket controls, established HTTP/2 DoH and DNS-gated browser loads')
    document.build(story,onFirstPage=page_number,onLaterPages=page_number)
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();root=args.root.resolve()
    original=load(root/'results/summary.json');repeat=load(root/'results/replication-2026-11-19/summary.json');check_summary(original,'Original');check_summary(repeat,'Replication')
    profile=load(root/'profile.json');references=load(root/'docs/references.json')['references']
    text=(root/'docs/paper_source.md').read_text(encoding='utf-8');tokens=make_tokens(root,original,repeat,references,profile)
    for key,value in tokens.items():text=text.replace('{{'+key+'}}',value)
    text=text.replace('](../figures/','](figures/')
    unknown=re.findall(r'\{\{(.*?)\}\}',text)
    if unknown:raise ValueError('Unfilled source fields '+str(unknown))
    abstract=text.split('### Abstract\n\n')[1].split('\n\nKeywords:')[0]
    counted=text.split('## References')[0];counted=re.sub(r'!\[[^\]]*\]\([^)]*\)','',counted);counted=re.sub(r'[|#*]',' ',counted);counted=re.sub(r'\n\s*[-: ]+\n','\n',counted)
    followup = load(root/'results/control_analysis.json')['control']
    sessions = load(root/'results/session_extension/summary.json')
    verification = load(root/'results/additional_date.json')
    repeatability = load(root/'results/repeatability/summary.json')
    repeatability_runs = [
        load(root/run['directory']/'environment.json')
        for run in repeatability['runs'] if run['status'] == 'complete'
    ]
    repeatability_attempts = sum(run['measured_rows'] for run in repeatability_runs)
    dates = {'2026-11-15', '2026-11-19', followup['date'], '2026-11-22', verification['started_utc'][:10]}
    dates.update(datetime.fromisoformat(run['started_utc']).astimezone(timezone(timedelta(hours=1))).date().isoformat()
                 for run in repeatability_runs)
    counts = {
        'main_words_including_abstract_tables_captions_declarations': len(counted.split()),
        'abstract_words': len(abstract.split()),
        'reference_count': len(references),
        'public_lookup_attempts_total': (
            3600 + followup['measured_attempts'] + extension_attempts(root, sessions)
            + verification['audit']['measured_attempts'] + repeatability_attempts
        ),
        'repeatability_attempts': repeatability_attempts,
        'browser_live_dns_fixture_attempts': 720,
        'browser_delay_injection_attempts': load(root/'results/browser-layout-2026-11-22/summary.json')['counts']['attempted'],
        'loopback_attempts': load(root/'results/loopback_summary.json')['attempts'],
        'dates': sorted(dates),
    }
    if not 250<=counts['abstract_words']<=300:raise ValueError('Abstract should contain 250–300 words: '+str(counts))
    if counts['main_words_including_abstract_tables_captions_declarations']>3000:raise ValueError('Conservative main-text count exceeds 3000: '+str(counts))
    output=render_pdf(text,root,profile);(root/'manuscript.md').write_text(text,encoding='utf-8');extended_results(root,original,repeat)
    counts['pdf']=output.name;(root/'results/paper_build.json').write_text(json.dumps(counts,indent=2)+'\n',encoding='utf-8');print(json.dumps(counts,indent=2))


if __name__=='__main__':main()

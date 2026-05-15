#!/usr/bin/env python3
"""SVN 日志与逐 revision diff 导出工具。

功能：
1. 生成 Markdown 格式的 SVN 日志。
2. 按日志中的每个 revision 导出单独 diff 文件。

交互模式：直接运行即可，会提示输入：
  - repo（默认当前目录）
  - path（默认 product）
  - revision start / end（end 默认 HEAD）
  - jobs（默认 8）

命令行模式示例：
  python scripts/svn_log_diff.py \
   --repo . \
   --path product \
   --rev-start 52330 \
   --rev-end HEAD \
   --jobs 8
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


def eprint(msg: str) -> None:
   sys.stderr.write(msg + "\n")


def prompt(text: str, default: str | None = None) -> str:
   if default is None or default == "":
      full = f"{text}: "
   else:
      full = f"{text} (默认 {default}): "
   value = input(full).strip()
   return value if value else (default or "")


def prompt_int(text: str, default: int | None = None) -> int:
   while True:
      value = prompt(text, str(default) if default is not None else None)
      try:
         return int(value)
      except ValueError:
         eprint("请输入数字版本号（例如 52330）")


def make_path_tag(path_value: str | None) -> str:
   if not path_value:
      return "repo"
   safe = path_value.replace("/", "_").replace("\\", "_").strip("_")
   return safe or "repo"


def ensure_dir(path: Path) -> None:
   path.mkdir(parents=True, exist_ok=True)


def normalize_multiline_text(text: str) -> list[str]:
   lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
   while lines and not lines[0]:
      lines.pop(0)
   while lines and not lines[-1]:
      lines.pop()
   return lines or ["（空）"]


def summarize_path_actions(paths: list[dict[str, str]]) -> dict[str, int]:
   summary = {"A": 0, "M": 0, "D": 0, "R": 0}
   for item in paths:
      action = item.get("action", "?")
      if action in summary:
         summary[action] += 1
   return summary


def first_non_empty_line(text: str) -> str:
   for line in normalize_multiline_text(text):
      stripped = line.strip()
      if stripped and stripped != "（空）":
         return stripped
   return "无明确提交说明"


def shorten_text(text: str, limit: int = 80) -> str:
   if len(text) <= limit:
      return text
   return text[: limit - 3].rstrip() + "..."


def quote_yaml_text(text: str) -> str:
   return text.replace("\\", "\\\\").replace('"', '\\"')


def relative_path_or_self(path: Path, base: Path) -> Path:
   try:
      return path.relative_to(base)
   except ValueError:
      return path


def run_svn_capture(cmd: list[str], cwd: Path) -> str:
   result = subprocess.run(
      cmd,
      cwd=str(cwd),
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      encoding="utf-8",
      errors="replace",
   )
   if result.returncode != 0:
      sys.stderr.write(result.stderr)
      raise RuntimeError(f"命令执行失败: {' '.join(cmd)}")
   return result.stdout


def run_svn_to_file(cmd: list[str], cwd: Path, output_path: Path) -> int:
   output_path.parent.mkdir(parents=True, exist_ok=True)
   with output_path.open("w", encoding="utf-8") as output_file:
      result = subprocess.run(
         cmd,
         cwd=str(cwd),
         stdout=subprocess.PIPE,
         stderr=subprocess.PIPE,
         encoding="utf-8",
         errors="replace",
      )
      if result.returncode == 0:
         output_file.write(result.stdout)
   if result.returncode != 0:
      sys.stderr.write(result.stderr)
   return result.returncode


def build_log_cmd(common: "CommonArgs", limit: int | None) -> list[str]:
   cmd = ["svn", "log", "--xml", "-v"]
   range_text = common.range_text()
   if range_text:
      cmd += ["-r", range_text]
   elif common.rev_start is not None:
      cmd += ["-r", str(common.rev_start)]
   if limit is not None:
      cmd += ["-l", str(limit)]
   if common.path:
      cmd.append(common.path)
   return cmd


def parse_log_entries(xml_text: str) -> list[dict]:
   root = ET.fromstring(xml_text)
   items: list[dict] = []
   for entry in root.findall("logentry"):
      rev_text = entry.get("revision")
      try:
         revision = int(rev_text) if rev_text is not None else None
      except ValueError:
         revision = None

      paths: list[dict[str, str]] = []
      paths_node = entry.find("paths")
      if paths_node is not None:
         for path_entry in paths_node.findall("path"):
            action = path_entry.get("action", "?")
            path_text = (path_entry.text or "").strip()
            if path_text:
               paths.append({"action": action, "path": path_text})

      items.append(
         {
            "revision": revision,
            "author": (entry.findtext("author") or "").strip() or "unknown",
            "date": (entry.findtext("date") or "").strip() or "unknown",
            "msg": (entry.findtext("msg") or "").strip(),
            "paths": paths,
         }
      )
   return items


def sort_items(items: list[dict]) -> list[dict]:
   return sorted(items, key=lambda x: (x.get("revision") is None, x.get("revision")))


def build_diff_file_name(common: "CommonArgs", revision: int | None) -> str:
   revision_text = str(revision) if revision is not None else "unknown"
   return f"r{revision_text}_{make_path_tag(common.path)}.diff"


def format_log_markdown(common: "CommonArgs", items: list[dict], log_output: Path, diff_outdir: Path) -> str:
   diff_outdir_rel = relative_path_or_self(diff_outdir, log_output.parent)
   lines = ["# SVN 变更包", ""]
   lines.append("## 总览")
   lines.append("")
   lines.append("| 项目 | 内容 |")
   lines.append("| --- | --- |")
   lines.append(f"| repo | {common.repo} |")
   lines.append(f"| path | {common.path or '.'} |")
   lines.append(f"| revision range | {common.range_text() or (common.rev_start or 'HEAD')} |")
   lines.append(f"| revision count | {len(items)} |")
   lines.append(f"| diff 目录 | {diff_outdir_rel} |")
   lines.append("")

   if not items:
      lines.append("## 无匹配 revision")
      lines.append("")
      return "\n".join(lines) + "\n"

   lines.append("## Revision 索引")
   lines.append("")
   lines.append("| Revision | Author | Date | 变更文件数 | 摘要提示 | Diff |")
   lines.append("| --- | --- | --- | ---: | --- | --- |")

   for item in items:
      revision = item.get("revision")
      paths = item.get("paths") or []
      diff_file_name = build_diff_file_name(common, revision)
      diff_link = f"[{diff_file_name}]({diff_outdir_rel.as_posix()}/{diff_file_name})"
      summary_hint = shorten_text(first_non_empty_line(item.get("msg") or ""), 40)
      lines.append(
         f"| [r{revision}](#r{revision}) | {item.get('author')} | {item.get('date')} | {len(paths)} | {summary_hint} | {diff_link} |"
      )
   lines.append("")

   lines.append("## LLM 快速索引")
   lines.append("")
   for item in items:
      revision = item.get("revision")
      paths = item.get("paths") or []
      diff_file_name = build_diff_file_name(common, revision)
      diff_file_path = f"{diff_outdir_rel.as_posix()}/{diff_file_name}"
      summary_hint = shorten_text(first_non_empty_line(item.get("msg") or ""), 80)
      lines.append("```yaml")
      lines.append(f"revision: r{revision}")
      lines.append(f"author: \"{quote_yaml_text(item.get('author') or 'unknown')}\"")
      lines.append(f"date: \"{quote_yaml_text(item.get('date') or 'unknown')}\"")
      lines.append(f"diff_file: \"{quote_yaml_text(diff_file_path)}\"")
      lines.append(f"summary_hint: \"{quote_yaml_text(summary_hint)}\"")
      lines.append(f"changed_paths_count: {len(paths)}")
      lines.append("```")
      lines.append("")

   lines.append("## Revision 详情")
   lines.append("")

   for item in items:
      revision = item.get("revision")
      diff_file_name = build_diff_file_name(common, revision)
      diff_link = f"[{diff_file_name}]({diff_outdir_rel.as_posix()}/{diff_file_name})"
      diff_file_path = f"{diff_outdir_rel.as_posix()}/{diff_file_name}"
      paths = item.get("paths") or []
      action_summary = summarize_path_actions(paths)
      summary_hint = first_non_empty_line(item.get("msg") or "")

      lines.append(f"## r{revision}")
      lines.append("")
      lines.append("| 字段 | 内容 |")
      lines.append("| --- | --- |")
      lines.append(f"| revision | r{revision} |")
      lines.append(f"| author | {item.get('author')} |")
      lines.append(f"| date | {item.get('date')} |")
      lines.append(f"| diff | {diff_link} |")
      lines.append(f"| diff_file | {diff_file_path} |")
      lines.append(f"| summary_hint | {summary_hint} |")
      lines.append(f"| file count | {len(paths)} |")
      lines.append(
         f"| action summary | A:{action_summary['A']} / M:{action_summary['M']} / D:{action_summary['D']} / R:{action_summary['R']} |"
      )
      lines.append("")

      lines.append("### LLM 映射字段")
      lines.append("")
      lines.append("```yaml")
      lines.append(f"revision: r{revision}")
      lines.append(f"diff_file: \"{quote_yaml_text(diff_file_path)}\"")
      lines.append(f"summary_hint: \"{quote_yaml_text(summary_hint)}\"")
      lines.append("```")
      lines.append("")

      lines.append("### 提交说明")
      lines.append("")
      for msg_line in normalize_multiline_text(item.get("msg") or ""):
         lines.append(f"> {msg_line}")
      lines.append("")

      if paths:
         lines.append("### 变更路径")
         lines.append("")
         lines.append("| 操作 | 路径 |")
         lines.append("| --- | --- |")
         for path_item in paths:
            lines.append(f"| {path_item.get('action')} | {path_item.get('path')} |")
         lines.append("")

   return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class CommonArgs:
   repo: Path
   path: str | None
   rev_start: str | None
   rev_end: str | None

   def range_text(self) -> str | None:
      if self.rev_start is None or self.rev_end is None:
         return None
      return f"{self.rev_start}:{self.rev_end}"


def default_output_base(repo: Path) -> Path:
   candidate = repo / "review_artifacts"
   if candidate.exists() and candidate.is_dir():
      return candidate
   return repo / "review_tmp"


def build_common_from_namespace(ns: argparse.Namespace) -> CommonArgs:
   repo = Path(ns.repo).resolve()
   if not repo.exists():
      raise SystemExit(f"repo 不存在: {repo}")
   path_value = ns.path.strip() if ns.path else None
   return CommonArgs(
      repo=repo,
      path=path_value or None,
      rev_start=ns.rev_start,
      rev_end=ns.rev_end,
   )


def default_targets(common: CommonArgs, base: Path) -> tuple[Path, Path]:
   path_tag = make_path_tag(common.path)
   range_tag = (
      f"r{common.rev_start}_{common.rev_end}"
      if common.rev_start is not None and common.rev_end is not None
      else "r"
   )
   log_md = base / f"svn_log_{path_tag}_{range_tag}.md"
   diffs_dir = base / f"svn_diffs_{path_tag}_{range_tag}"
   return log_md, diffs_dir


def export_single_revision_diff(common: CommonArgs, revision: int, outdir: Path) -> int:
   output_path = outdir / build_diff_file_name(common, revision)
   cmd = ["svn", "diff", "-c", str(revision)]
   if common.path:
      cmd.append(common.path)
   return run_svn_to_file(cmd, common.repo, output_path)


def export_revision_diffs(common: CommonArgs, revisions: list[int], outdir: Path, jobs: int) -> int:
   ensure_dir(outdir)

   def task(revision: int) -> int:
      return export_single_revision_diff(common, revision, outdir)

   if jobs > 1:
      eprint(f"并行导出 diff，线程数: {jobs}")
      with ThreadPoolExecutor(max_workers=jobs) as executor:
         return_codes = list(executor.map(task, revisions))
      for return_code in return_codes:
         if return_code != 0:
            return return_code
      return 0

   for revision in revisions:
      return_code = task(revision)
      if return_code != 0:
         return return_code
   return 0


def cmd_export(common: CommonArgs, log_output: Path, diff_outdir: Path, jobs: int, limit: int | None) -> int:
   try:
      xml_text = run_svn_capture(build_log_cmd(common, limit=limit), common.repo)
   except RuntimeError:
      return 1

   items = sort_items(parse_log_entries(xml_text))
   revisions = [item["revision"] for item in items if item.get("revision") is not None]

   log_output.parent.mkdir(parents=True, exist_ok=True)
   log_output.write_text(format_log_markdown(common, items, log_output, diff_outdir), encoding="utf-8")

   if not revisions:
      eprint("未找到匹配的 revision，仅输出 Markdown 日志")
      return 0

   return export_revision_diffs(common, revisions, diff_outdir, jobs=jobs)


def interactive_wizard() -> int:
   eprint("进入交互模式（直接回车使用默认值）")

   repo = Path(prompt("repo 工作副本目录", ".")).resolve()
   if not repo.exists():
      eprint(f"repo 不存在: {repo}")
      return 2

   path_value = prompt("限定 path", "product").strip() or None
   rev_start = str(prompt_int("起始 revision"))
   rev_end = prompt("结束 revision", "HEAD")
   jobs = prompt_int("并行线程数 (jobs)", 8)

   common = CommonArgs(repo=repo, path=path_value, rev_start=rev_start, rev_end=rev_end)
   base = default_output_base(repo)
   ensure_dir(base)
   log_output, diff_outdir = default_targets(common, base)

   eprint(f"输出 Markdown 日志 -> {log_output}")
   eprint(f"输出 diff 目录 -> {diff_outdir}")
   return cmd_export(common, log_output, diff_outdir, jobs=jobs, limit=None)


def main(argv: list[str] | None = None) -> int:
   parser = argparse.ArgumentParser(description="SVN Markdown 日志与逐 revision diff 导出工具")
   parser.add_argument("--interactive", action="store_true", help="强制进入交互模式")
   parser.add_argument("--repo", default=".", help="SVN 工作副本目录（默认当前目录）")
   parser.add_argument("--path", default="product", help="限定到子路径或文件（默认 product）")
   parser.add_argument("--rev-start", help="起始 revision（例如 52330）")
   parser.add_argument("--rev-end", default="HEAD", help="结束 revision（默认 HEAD）")
   parser.add_argument("--limit", type=int, help="限制日志条数")
   parser.add_argument("--jobs", type=int, default=8, help="并行导出 diff 的线程数（默认 8）")
   parser.add_argument("--log-output", help="Markdown 日志输出路径")
   parser.add_argument("--diff-outdir", help="逐 revision diff 输出目录")

   args = parser.parse_args(argv)

   if args.interactive or len(sys.argv) == 1:
      return interactive_wizard()

   common = build_common_from_namespace(args)
   base = default_output_base(common.repo)
   ensure_dir(base)
   default_log_output, default_diff_outdir = default_targets(common, base)

   log_output = Path(args.log_output).resolve() if args.log_output else default_log_output
   diff_outdir = Path(args.diff_outdir).resolve() if args.diff_outdir else default_diff_outdir

   eprint(f"输出 Markdown 日志 -> {log_output}")
   eprint(f"输出 diff 目录 -> {diff_outdir}")
   return cmd_export(common, log_output, diff_outdir, jobs=args.jobs, limit=args.limit)


if __name__ == "__main__":
   raise SystemExit(main())
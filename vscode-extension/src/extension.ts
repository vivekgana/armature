/**
 * Armature VS Code Extension
 *
 * Runs `armature check --file <path> --json` on every file save, parses the
 * JSON results, and surfaces violations in the VS Code Problems panel via a
 * DiagnosticCollection.
 *
 * Commands:
 *   armature.runCheck      -- run project-wide check
 *   armature.runCheckFile  -- run check on the active file
 *   armature.runHeal       -- run self-healing pipeline
 */

import * as vscode from 'vscode';
import { execFile } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';

const execFileAsync = promisify(execFile);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CheckResult {
  name: string;
  passed: boolean;
  violations: number;
  details: string;
  score?: number;
  weight?: number;
}

// ---------------------------------------------------------------------------
// Extension state
// ---------------------------------------------------------------------------

let diagnosticCollection: vscode.DiagnosticCollection;
let statusBarItem: vscode.StatusBarItem;

// ---------------------------------------------------------------------------
// Activation
// ---------------------------------------------------------------------------

export function activate(context: vscode.ExtensionContext): void {
  diagnosticCollection = vscode.languages.createDiagnosticCollection('armature');
  context.subscriptions.push(diagnosticCollection);

  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusBarItem.command = 'armature.runCheck';
  statusBarItem.text = '$(shield) Armature';
  statusBarItem.tooltip = 'Click to run Armature quality check';
  context.subscriptions.push(statusBarItem);

  const cfg = vscode.workspace.getConfiguration('armature');
  if (cfg.get<boolean>('showStatusBar', true)) {
    statusBarItem.show();
  }

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand('armature.runCheck', () => runCheck(null)),
    vscode.commands.registerCommand('armature.runCheckFile', () => {
      const editor = vscode.window.activeTextEditor;
      runCheck(editor?.document.uri.fsPath ?? null);
    }),
    vscode.commands.registerCommand('armature.runHeal', runHeal),
  );

  // Check-on-save
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      const config = vscode.workspace.getConfiguration('armature');
      if (config.get<boolean>('checkOnSave', true)) {
        runCheck(doc.uri.fsPath);
      }
    }),
  );
}

export function deactivate(): void {
  diagnosticCollection?.clear();
  diagnosticCollection?.dispose();
}

// ---------------------------------------------------------------------------
// Core runners
// ---------------------------------------------------------------------------

async function runCheck(filePath: string | null): Promise<void> {
  const workspaceRoot = getWorkspaceRoot();
  if (!workspaceRoot) {
    return;
  }

  const cfg = vscode.workspace.getConfiguration('armature');
  const executable = cfg.get<string>('executablePath', 'armature');
  const args = filePath
    ? ['check', '--file', filePath, '--json']
    : ['check', '--json'];

  statusBarItem.text = '$(sync~spin) Armature…';

  try {
    const { stdout } = await execFileAsync(executable, args, {
      cwd: workspaceRoot,
      timeout: 60_000,
    });
    const results: CheckResult[] = JSON.parse(stdout);
    updateDiagnostics(results, workspaceRoot, filePath);
    updateStatusBar(results);
  } catch (err: unknown) {
    // Non-zero exit = check failures; stderr has details
    const error = err as NodeJS.ErrnoException & { stdout?: string };
    if (error.stdout) {
      try {
        const results: CheckResult[] = JSON.parse(error.stdout);
        updateDiagnostics(results, workspaceRoot, filePath);
        updateStatusBar(results);
        return;
      } catch {
        // fall through to generic error handling
      }
    }
    statusBarItem.text = '$(error) Armature';
    vscode.window.showWarningMessage(`Armature: could not run check — ${String(err)}`);
  }
}

async function runHeal(): Promise<void> {
  const workspaceRoot = getWorkspaceRoot();
  if (!workspaceRoot) {
    return;
  }

  const cfg = vscode.workspace.getConfiguration('armature');
  const executable = cfg.get<string>('executablePath', 'armature');

  try {
    await execFileAsync(executable, ['heal'], { cwd: workspaceRoot, timeout: 120_000 });
    vscode.window.showInformationMessage('Armature: self-healing completed.');
    runCheck(null); // re-check after heal
  } catch {
    vscode.window.showWarningMessage('Armature: heal did not fully resolve all failures. Check the terminal.');
  }
}

// ---------------------------------------------------------------------------
// Diagnostics
// ---------------------------------------------------------------------------

function updateDiagnostics(
  results: CheckResult[],
  workspaceRoot: string,
  filePath: string | null,
): void {
  if (filePath) {
    // Clear only the checked file's diagnostics
    diagnosticCollection.delete(vscode.Uri.file(filePath));
  } else {
    diagnosticCollection.clear();
  }

  for (const result of results) {
    if (result.passed || result.violations === 0) {
      continue;
    }
    // File-level diagnostic when we don't have line-level detail
    const target = filePath ?? path.join(workspaceRoot, 'armature.yaml');
    const uri = vscode.Uri.file(target);
    const range = new vscode.Range(0, 0, 0, 0);
    const diag = new vscode.Diagnostic(
      range,
      `[armature/${result.name}] ${result.details} (${result.violations} violation(s))`,
      result.violations > 3 ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning,
    );
    diag.source = 'armature';
    diag.code = result.name;

    const existing = diagnosticCollection.get(uri) ?? [];
    diagnosticCollection.set(uri, [...existing, diag]);
  }
}

function updateStatusBar(results: CheckResult[]): void {
  const totalWeight = results.reduce((s, r) => s + (r.weight ?? 25), 0);
  const weightedScore = totalWeight > 0
    ? results.reduce((s, r) => s + (r.score ?? (r.passed ? 1 : 0)) * (r.weight ?? 25), 0) / totalWeight
    : 1;

  const pct = Math.round(weightedScore * 100);
  const allPassed = results.every((r) => r.passed);
  const icon = allPassed ? '$(pass-filled)' : '$(error)';
  const gate = weightedScore >= 0.95 ? 'merge' : weightedScore >= 0.85 ? 'review' : 'draft';

  statusBarItem.text = `${icon} Armature ${pct}% (${gate})`;
  statusBarItem.backgroundColor = allPassed
    ? undefined
    : new vscode.ThemeColor('statusBarItem.errorBackground');
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getWorkspaceRoot(): string | null {
  const folders = vscode.workspace.workspaceFolders;
  return folders && folders.length > 0 ? folders[0].uri.fsPath : null;
}

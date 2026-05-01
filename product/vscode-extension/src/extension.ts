import * as vscode from 'vscode';
import * as path from 'path';
import * as http from 'http';
import { ChildProcess, spawn } from 'child_process';

const DEFAULT_HCR_PORT = 8733;
const HCR_HOST = '127.0.0.1';

let lastFocusTime: Date = new Date();
let lastActiveFile = '';
let outputChannel: vscode.OutputChannel;
let statusBarItem: vscode.StatusBarItem;
let engineProcess: ChildProcess | undefined;
let serverStartPromise: Promise<void> | undefined;

export function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('HCR Assistant');

    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command = 'hcr.resume';
    statusBarItem.text = '$(history) HCR';
    statusBarItem.tooltip = 'Click to resume session';
    context.subscriptions.push(statusBarItem, outputChannel);

    context.subscriptions.push(
        vscode.commands.registerCommand('hcr.resume', () => runResume()),
        vscode.commands.registerCommand('hcr.showState', () => showState()),
        vscode.commands.registerCommand('hcr.clearState', () => clearState()),
        vscode.commands.registerCommand('hcr.startServer', () => startEngineServer(true))
    );

    setupFileWatcher(context);
    setupActiveTabTracker(context);

    const config = vscode.workspace.getConfiguration('hcr');
    if (config.get('autoResume', true)) {
        setupAutoResume(context);
    }

    setupHeartbeat(context);

    startEngineServer(false)
        .then(() => checkForExistingState())
        .catch((error) => outputChannel.appendLine(`[HCR] Startup check skipped: ${String(error)}`));

    outputChannel.appendLine('[HCR] Extension activated');
}

function getWorkspaceRoot(): string | undefined {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    return workspaceFolders?.[0]?.uri.fsPath;
}

function getPort(): number {
    return vscode.workspace.getConfiguration('hcr').get<number>('serverPort', DEFAULT_HCR_PORT);
}

function getLaunchConfig(workspaceRoot: string): { command: string; args: string[]; cwd: string } {
    const config = vscode.workspace.getConfiguration('hcr');
    const configuredCommand = config.get<string>('commandPath', '').trim();
    const configuredPython = config.get<string>('pythonPath', '').trim();

    if (configuredCommand) {
        return {
            command: configuredCommand,
            args: ['resume', '--server', '--project', workspaceRoot, '--port', String(getPort())],
            cwd: workspaceRoot
        };
    }

    const pythonExecutable = configuredPython || process.env.PYTHON || 'python';
    return {
        command: pythonExecutable,
        args: ['-m', 'product.cli.resume', '--server', '--project', workspaceRoot, '--port', String(getPort())],
        cwd: workspaceRoot
    };
}

async function hcrRequest(endpoint: string, method = 'GET', data?: unknown): Promise<any> {
    return new Promise((resolve, reject) => {
        const payload = data ? JSON.stringify(data) : undefined;
        const req = http.request(
            {
                hostname: HCR_HOST,
                port: getPort(),
                path: endpoint,
                method,
                headers: payload ? {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(payload)
                } : undefined
            },
            (res) => {
                let body = '';
                res.on('data', (chunk) => {
                    body += chunk;
                });
                res.on('end', () => {
                    if (res.statusCode && res.statusCode >= 400) {
                        reject(new Error(body || `HTTP ${res.statusCode}`));
                        return;
                    }
                    try {
                        resolve(body ? JSON.parse(body) : {});
                    } catch {
                        resolve(body);
                    }
                });
            }
        );

        req.on('error', reject);
        req.setTimeout(2000, () => req.destroy(new Error('request timeout')));

        if (payload) {
            req.write(payload);
        }

        req.end();
    });
}

async function waitForServerReady(attempts = 20, delayMs = 500): Promise<void> {
    for (let attempt = 0; attempt < attempts; attempt++) {
        try {
            await hcrRequest('/health');
            return;
        } catch {
            await new Promise((resolve) => setTimeout(resolve, delayMs));
        }
    }
    throw new Error('engine server did not become ready');
}

async function startEngineServer(showMessages: boolean): Promise<void> {
    const workspaceRoot = getWorkspaceRoot();
    if (!workspaceRoot) {
        return;
    }

    try {
        await hcrRequest('/health');
        return;
    } catch {
        // server is not up; continue
    }

    if (serverStartPromise) {
        return serverStartPromise;
    }

    serverStartPromise = (async () => {
        const launch = getLaunchConfig(workspaceRoot);
        outputChannel.appendLine(`[HCR] Starting engine server with: ${launch.command} ${launch.args.join(' ')}`);

        engineProcess?.kill();
        engineProcess = spawn(launch.command, launch.args, {
            cwd: launch.cwd,
            detached: process.platform !== 'win32',
            stdio: 'ignore',
            windowsHide: true
        });

        engineProcess.on('exit', (code, signal) => {
            outputChannel.appendLine(`[HCR] Engine server exited (code=${code ?? 'null'}, signal=${signal ?? 'null'})`);
            engineProcess = undefined;
        });

        try {
            await waitForServerReady();
            if (showMessages) {
                vscode.window.showInformationMessage('HCR engine server started');
            }
        } catch (error) {
            engineProcess = undefined;
            throw error;
        } finally {
            serverStartPromise = undefined;
        }
    })();

    return serverStartPromise;
}

async function runResume(): Promise<void> {
    outputChannel.clear();
    outputChannel.show(true);
    outputChannel.appendLine('[HCR] Analyzing session context...');

    try {
        await startEngineServer(false);

        const now = new Date();
        const idleMinutes = (now.getTime() - lastFocusTime.getTime()) / (1000 * 60);
        const result = await hcrRequest('/resume', 'POST', { gap_minutes: idleMinutes });

        displayResults(result);
        updateStatusBar(result);
        await vscode.commands.executeCommand('setContext', 'hcr.hasState', true);
    } catch (error) {
        outputChannel.appendLine(`[HCR Error] ${String(error)}`);
        vscode.window.showErrorMessage(`HCR: Failed to resume session (${String(error)})`);
    }
}

function displayResults(context: any): void {
    outputChannel.appendLine('');
    outputChannel.appendLine('='.repeat(60));
    outputChannel.appendLine('  HCR SESSION RESUME');
    outputChannel.appendLine('='.repeat(60));
    outputChannel.appendLine('');

    const gap = context?.gap_minutes;
    if (gap !== null && gap !== undefined) {
        if (gap < 1) {
            outputChannel.appendLine('[TIME] Last active: Just now');
        } else if (gap < 60) {
            outputChannel.appendLine(`[TIME] Last active: ${Math.round(gap)} minutes ago`);
        } else {
            outputChannel.appendLine(`[TIME] Last active: ${Math.round(gap / 60)} hours ago`);
        }
        outputChannel.appendLine('');
    }

    outputChannel.appendLine(`[TASK] ${context?.current_task ?? 'Unknown'}`);
    outputChannel.appendLine('');
    outputChannel.appendLine(`[PROGRESS] ${context?.progress_percent ?? 0}%`);
    const filled = Math.max(0, Math.min(20, Math.round((context?.progress_percent ?? 0) / 5)));
    const bar = '#'.repeat(filled) + '-'.repeat(20 - filled);
    outputChannel.appendLine(`           [${bar}]`);
    outputChannel.appendLine('');
    outputChannel.appendLine(`[ACTION] ${context?.next_action ?? 'Unknown'}`);
    outputChannel.appendLine('');

    if ((context?.confidence ?? 0) > 0.7) {
        outputChannel.appendLine('[OK] High confidence in this assessment');
    } else if ((context?.confidence ?? 0) > 0.4) {
        outputChannel.appendLine('[!] Moderate confidence - verify this makes sense');
    } else {
        outputChannel.appendLine("[?] Low confidence - please clarify what you're working on");
    }

    if (Array.isArray(context?.facts) && context.facts.length > 0) {
        outputChannel.appendLine('');
        outputChannel.appendLine('[CONTEXT]');
        for (const fact of context.facts.slice(0, 5)) {
            outputChannel.appendLine(`  - ${fact}`);
        }
    }

    outputChannel.appendLine('');
    outputChannel.appendLine('='.repeat(60));
}

async function showState(): Promise<void> {
    outputChannel.show(true);
    outputChannel.appendLine('[HCR] Current session state:');

    try {
        await startEngineServer(false);
        const result = await hcrRequest('/context');
        displayResults(result);
    } catch (error) {
        outputChannel.appendLine(`[HCR Error] ${String(error)}`);
    }
}

async function clearState(): Promise<void> {
    try {
        await startEngineServer(false);
        await hcrRequest('/state/clear', 'GET');
        vscode.window.showInformationMessage('HCR: Session state cleared');
        await vscode.commands.executeCommand('setContext', 'hcr.hasState', false);
        statusBarItem.hide();
    } catch {
        vscode.window.showInformationMessage('HCR: No state to clear');
    }
}

function setupFileWatcher(context: vscode.ExtensionContext): void {
    const disposable = vscode.workspace.onDidSaveTextDocument(async (doc) => {
        try {
            await startEngineServer(false);
            await hcrRequest('/event', 'POST', {
                type: 'file_edit',
                data: { path: doc.fileName }
            });
            outputChannel.appendLine(`[HCR] Updated state: ${path.basename(doc.fileName)} saved`);
        } catch {
            // keep editor quiet on background tracking failures
        }
    });

    context.subscriptions.push(disposable);
}

function setupActiveTabTracker(context: vscode.ExtensionContext): void {
    const disposable = vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (!editor) {
            return;
        }

        lastActiveFile = editor.document.fileName;
        hcrRequest('/event', 'POST', {
            type: 'file_focus',
            data: { path: editor.document.fileName, language: editor.document.languageId }
        }).catch(() => undefined);
    });

    context.subscriptions.push(disposable);
}

function setupHeartbeat(context: vscode.ExtensionContext): void {
    const interval = setInterval(async () => {
        try {
            await hcrRequest('/health');
        } catch {
            outputChannel.appendLine('[HCR] Server not responding, attempting restart...');
            try {
                await startEngineServer(false);
            } catch (error) {
                outputChannel.appendLine(`[HCR] Restart failed: ${String(error)}`);
            }
        }
    }, 30000);

    context.subscriptions.push({ dispose: () => clearInterval(interval) });
}

function setupAutoResume(context: vscode.ExtensionContext): void {
    const disposable = vscode.window.onDidChangeWindowState((e) => {
        if (!e.focused) {
            return;
        }

        const now = new Date();
        const idleMinutes = (now.getTime() - lastFocusTime.getTime()) / (1000 * 60);
        const threshold = vscode.workspace.getConfiguration('hcr').get<number>('idleThreshold', 30);

        if (idleMinutes > threshold) {
            outputChannel.appendLine(`[HCR] Auto-resuming after ${Math.round(idleMinutes)} minutes idle`);
            void runResume();
        }

        lastFocusTime = now;
    });

    context.subscriptions.push(disposable);
}

function updateStatusBar(context: any): void {
    const task = context?.current_task || 'Unknown';
    const progress = context?.progress_percent || 0;
    const truncated = task.length > 20 ? `${task.substring(0, 20)}...` : task;

    statusBarItem.text = `$(history) ${progress}% - ${truncated}`;
    statusBarItem.tooltip = `Task: ${task}\nProgress: ${progress}%\nFile: ${lastActiveFile || 'unknown'}`;
    statusBarItem.show();
}

async function checkForExistingState(): Promise<void> {
    try {
        await startEngineServer(false);
        const result = await hcrRequest('/state/exists');

        if (result?.exists) {
            await vscode.commands.executeCommand('setContext', 'hcr.hasState', true);
            statusBarItem.show();

            const config = vscode.workspace.getConfiguration('hcr');
            if (config.get('autoResume', true)) {
                void runResume();
            }
        } else {
            await vscode.commands.executeCommand('setContext', 'hcr.hasState', false);
        }
    } catch {
        await vscode.commands.executeCommand('setContext', 'hcr.hasState', false);
    }
}

export function deactivate() {
    outputChannel.dispose();
    statusBarItem.dispose();
    engineProcess?.kill();
}

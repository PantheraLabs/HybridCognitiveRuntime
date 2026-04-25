import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';

const execAsync = promisify(exec);

// Global state
let lastFocusTime: Date = new Date();
let outputChannel: vscode.OutputChannel;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    // Create output channel
    outputChannel = vscode.window.createOutputChannel('HCR Assistant');
    
    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command = 'hcr.resume';
    context.subscriptions.push(statusBarItem);
    
    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('hcr.resume', () => runResumeCommand(false))
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('hcr.showState', () => showCurrentState())
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('hcr.clearState', () => clearState())
    );
    
    // Set up window focus tracking for auto-resume
    const config = vscode.workspace.getConfiguration('hcr');
    if (config.get('autoResume', true)) {
        setupAutoResume();
    }
    
    // Initial check - if we have state, show it
    checkForExistingState();
    
    outputChannel.appendLine('[HCR] Extension activated');
}

async function runResumeCommand(autoMode: boolean): Promise<void> {
    const config = vscode.workspace.getConfiguration('hcr');
    const format = config.get('outputFormat', 'text');
    
    outputChannel.clear();
    outputChannel.show(true);
    outputChannel.appendLine('[HCR] Analyzing session context...');
    
    try {
        // Find workspace root
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showWarningMessage('HCR: No workspace open');
            return;
        }
        
        const workspaceRoot = workspaceFolders[0].uri.fsPath;
        
        // Build command
        const autoFlag = autoMode ? '--auto' : '';
        const cmd = `python -m product.cli.resume ${autoFlag} --format ${format}`;
        
        // Execute
        const { stdout, stderr } = await execAsync(cmd, {
            cwd: workspaceRoot,
            timeout: 10000
        });
        
        if (stderr) {
            outputChannel.appendLine(`[HCR Warning] ${stderr}`);
        }
        
        // Display results
        outputChannel.appendLine(stdout);
        
        // Parse JSON if that's the format
        if (format === 'json') {
            try {
                const result = JSON.parse(stdout);
                updateStatusBar(result.session_resume);
            } catch {
                // Ignore parse errors
            }
        } else {
            // Update status bar with simple text parsing
            updateStatusBarFromText(stdout);
        }
        
        // Set context for tree view
        vscode.commands.executeCommand('setContext', 'hcr.hasState', true);
        
    } catch (error) {
        outputChannel.appendLine(`[HCR Error] ${error}`);
        vscode.window.showErrorMessage('HCR: Failed to resume session');
    }
}

async function showCurrentState(): Promise<void> {
    outputChannel.show(true);
    outputChannel.appendLine('[HCR] Current session state:');
    await runResumeCommand(true);
}

async function clearState(): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return;
    
    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const statePath = path.join(workspaceRoot, '.hcr', 'session_state.json');
    
    try {
        const fs = require('fs').promises;
        await fs.unlink(statePath);
        vscode.window.showInformationMessage('HCR: Session state cleared');
        vscode.commands.executeCommand('setContext', 'hcr.hasState', false);
        statusBarItem.hide();
    } catch {
        // File might not exist
        vscode.window.showInformationMessage('HCR: No state to clear');
    }
}

function setupAutoResume(): void {
    // Track window focus
    vscode.window.onDidChangeWindowState((e) => {
        if (e.focused) {
            const now = new Date();
            const idleMinutes = (now.getTime() - lastFocusTime.getTime()) / (1000 * 60);
            
            const config = vscode.workspace.getConfiguration('hcr');
            const threshold = config.get('idleThreshold', 30);
            
            if (idleMinutes > threshold) {
                // Trigger auto-resume
                outputChannel.appendLine(`[HCR] Auto-resuming after ${Math.round(idleMinutes)} minutes idle`);
                runResumeCommand(true);
            }
            
            lastFocusTime = now;
        }
    });
}

async function checkForExistingState(): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return;
    
    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const statePath = path.join(workspaceRoot, '.hcr', 'session_state.json');
    
    try {
        const fs = require('fs').promises;
        await fs.access(statePath);
        
        // State exists, show it
        vscode.commands.executeCommand('setContext', 'hcr.hasState', true);
        statusBarItem.text = "$(history) HCR";
        statusBarItem.tooltip = "Click to resume session";
        statusBarItem.show();
        
        // Optionally auto-resume on startup
        const config = vscode.workspace.getConfiguration('hcr');
        if (config.get('autoResume', true)) {
            runResumeCommand(true);
        }
    } catch {
        // No state yet
        vscode.commands.executeCommand('setContext', 'hcr.hasState', false);
    }
}

function updateStatusBar(sessionData: any): void {
    const task = sessionData?.current_task || 'Unknown';
    const progress = sessionData?.progress_percent || 0;
    
    statusBarItem.text = `$(history) ${progress}% - ${task.substring(0, 20)}...`;
    statusBarItem.tooltip = `Task: ${task}\nProgress: ${progress}%`;
    statusBarItem.show();
}

function updateStatusBarFromText(text: string): void {
    // Simple parsing of text output
    const taskMatch = text.match(/Current Task:\s*(.+)/);
    const progressMatch = text.match(/Progress:\s*(\d+)%/);
    
    if (taskMatch && progressMatch) {
        const task = taskMatch[1].trim().substring(0, 20);
        const progress = progressMatch[1];
        statusBarItem.text = `$(history) ${progress}% - ${task}...`;
        statusBarItem.show();
    }
}

export function deactivate() {
    outputChannel.dispose();
    statusBarItem.dispose();
}

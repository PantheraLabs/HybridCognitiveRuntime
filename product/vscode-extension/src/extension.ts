import * as vscode from 'vscode';
import * as path from 'path';
import * as http from 'http';

// HCR Engine Server config
const HCR_PORT = 8733;
const HCR_HOST = 'localhost';

// Global state
let lastFocusTime: Date = new Date();
let outputChannel: vscode.OutputChannel;
let statusBarItem: vscode.StatusBarItem;
let engineServer: vscode.Terminal | undefined;

export function activate(context: vscode.ExtensionContext) {
    // Create output channel
    outputChannel = vscode.window.createOutputChannel('HCR Assistant');
    
    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command = 'hcr.resume';
    statusBarItem.text = "$(history) HCR";
    statusBarItem.tooltip = "Click to resume session";
    context.subscriptions.push(statusBarItem);
    
    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('hcr.resume', () => runResume())
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('hcr.showState', () => showState())
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('hcr.clearState', () => clearState())
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('hcr.startServer', () => startEngineServer())
    );
    
    // Set up file watchers for state updates
    setupFileWatcher(context);
    
    // Set up window focus tracking for auto-resume
    const config = vscode.workspace.getConfiguration('hcr');
    if (config.get('autoResume', true)) {
        setupAutoResume();
    }
    
    // Start engine server and initial check
    startEngineServer().then(() => {
        checkForExistingState();
    });
    
    outputChannel.appendLine('[HCR] Extension activated');
}

// HTTP client for HCR Engine
async function hcrRequest(endpoint: string, method: string = 'GET', data?: any): Promise<any> {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: HCR_HOST,
            port: HCR_PORT,
            path: endpoint,
            method: method,
            headers: data ? {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(JSON.stringify(data))
            } : {}
        };
        
        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(body));
                } catch {
                    resolve(body);
                }
            });
        });
        
        req.on('error', (err) => reject(err));
        
        if (data) {
            req.write(JSON.stringify(data));
        }
        
        req.end();
    });
}

async function startEngineServer(): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return;
    
    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    
    // Check if server is already running
    try {
        await hcrRequest('/health');
        outputChannel.appendLine('[HCR] Engine server already running');
        return;
    } catch {
        // Server not running, start it
    }
    
    outputChannel.appendLine('[HCR] Starting engine server...');
    
    // Start server in integrated terminal
    engineServer = vscode.window.createTerminal({
        name: 'HCR Engine',
        cwd: workspaceRoot,
        hideFromUser: true  // Run in background
    });
    
    engineServer.sendText(`python -m product.cli.resume --server --project "${workspaceRoot}"`);
    
    // Wait for server to start
    let attempts = 0;
    while (attempts < 10) {
        await new Promise(r => setTimeout(r, 500));
        try {
            await hcrRequest('/health');
            outputChannel.appendLine('[HCR] Engine server started');
            return;
        } catch {
            attempts++;
        }
    }
    
    vscode.window.showErrorMessage('HCR: Failed to start engine server');
}

async function runResume(): Promise<void> {
    outputChannel.clear();
    outputChannel.show(true);
    outputChannel.appendLine('[HCR] Analyzing session context...');
    
    try {
        // Ensure server is running
        await startEngineServer();
        
        // Calculate idle time
        const now = new Date();
        const idleMinutes = (now.getTime() - lastFocusTime.getTime()) / (1000 * 60);
        
        // Call engine directly via HTTP
        const result = await hcrRequest('/resume', 'POST', {
            gap_minutes: idleMinutes
        });
        
        // Display results
        displayResults(result);
        
        // Update status bar
        updateStatusBar(result);
        
        // Set context for tree view
        vscode.commands.executeCommand('setContext', 'hcr.hasState', true);
        
    } catch (error) {
        outputChannel.appendLine(`[HCR Error] ${error}`);
        vscode.window.showErrorMessage('HCR: Failed to resume session');
    }
}

function displayResults(context: any): void {
    outputChannel.appendLine('');
    outputChannel.appendLine('='.repeat(60));
    outputChannel.appendLine('  HCR SESSION RESUME');
    outputChannel.appendLine('='.repeat(60));
    outputChannel.appendLine('');
    
    // Time gap
    const gap = context.gap_minutes;
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
    
    // Task
    outputChannel.appendLine(`[TASK] ${context.current_task}`);
    outputChannel.appendLine('');
    
    // Progress
    outputChannel.appendLine(`[PROGRESS] ${context.progress_percent}%`);
    const filled = Math.round(context.progress_percent / 5);
    const bar = '#'.repeat(filled) + '-'.repeat(20 - filled);
    outputChannel.appendLine(`           [${bar}]`);
    outputChannel.appendLine('');
    
    // Action
    outputChannel.appendLine(`[ACTION] ${context.next_action}`);
    outputChannel.appendLine('');
    
    // Confidence
    if (context.confidence > 0.7) {
        outputChannel.appendLine('[OK] High confidence in this assessment');
    } else if (context.confidence > 0.4) {
        outputChannel.appendLine('[!] Moderate confidence - verify this makes sense');
    } else {
        outputChannel.appendLine('[?] Low confidence - please clarify what you\'re working on');
    }
    
    // Context facts
    if (context.facts && context.facts.length > 0) {
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
        await startEngineServer();
        const result = await hcrRequest('/context');
        displayResults(result);
    } catch (error) {
        outputChannel.appendLine(`[HCR Error] ${error}`);
    }
}

async function clearState(): Promise<void> {
    try {
        await startEngineServer();
        await hcrRequest('/state/clear', 'GET');
        vscode.window.showInformationMessage('HCR: Session state cleared');
        vscode.commands.executeCommand('setContext', 'hcr.hasState', false);
        statusBarItem.hide();
    } catch {
        vscode.window.showInformationMessage('HCR: No state to clear');
    }
}

function setupFileWatcher(context: vscode.ExtensionContext): void {
    // Watch for file saves to update state
    const disposable = vscode.workspace.onDidSaveTextDocument(async (doc) => {
        try {
            await startEngineServer();
            await hcrRequest('/event', 'POST', {
                type: 'file_edit',
                data: { path: doc.fileName }
            });
            outputChannel.appendLine(`[HCR] Updated state: ${path.basename(doc.fileName)} saved`);
        } catch {
            // Ignore errors
        }
    });
    
    context.subscriptions.push(disposable);
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
                runResume();
            }
            
            lastFocusTime = now;
        }
    });
}

function updateStatusBar(context: any): void {
    const task = context?.current_task || 'Unknown';
    const progress = context?.progress_percent || 0;
    
    statusBarItem.text = `$(history) ${progress}% - ${task.substring(0, 20)}...`;
    statusBarItem.tooltip = `Task: ${task}\nProgress: ${progress}%`;
    statusBarItem.show();
}

async function checkForExistingState(): Promise<void> {
    try {
        await startEngineServer();
        const result = await hcrRequest('/state/exists');
        
        if (result.exists) {
            vscode.commands.executeCommand('setContext', 'hcr.hasState', true);
            statusBarItem.show();
            
            // Optionally auto-resume
            const config = vscode.workspace.getConfiguration('hcr');
            if (config.get('autoResume', true)) {
                runResume();
            }
        } else {
            vscode.commands.executeCommand('setContext', 'hcr.hasState', false);
        }
    } catch {
        // Server not ready yet
        vscode.commands.executeCommand('setContext', 'hcr.hasState', false);
    }
}

export function deactivate() {
    outputChannel.dispose();
    statusBarItem.dispose();
    
    // Kill engine server terminal
    if (engineServer) {
        engineServer.dispose();
    }
}

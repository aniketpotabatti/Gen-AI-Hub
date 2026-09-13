import * as vscode from "vscode";

const gateway = vscode.workspace.getConfiguration("codesense").get<string>("gatewayUrl", "http://localhost:8787");
export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(vscode.commands.registerCommand("codesense.explainSelection", async () => {
    const editor = vscode.window.activeTextEditor; if (!editor) return;
    const selection = editor.selection; const snippet = editor.document.getText(selection.isEmpty ? undefined : selection);
    const position = editor.selection.active;
    const response = await fetch(`${gateway}/api/codesense`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: "explain", language: editor.document.languageId, snippet, cursorLine: position.line + 1, cursorCol: position.character + 1 }) });
    if (!response.ok || !response.body) return vscode.window.showErrorMessage("CodeSense gateway is unavailable.");
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let output = "";
    for (;;) { const { value, done } = await reader.read(); if (done) break; for (const row of decoder.decode(value).split("\n")) if (row.startsWith("data: ")) { const data = JSON.parse(row.slice(6)); if (data !== "[DONE]" && data.delta) output += data.delta; } }
    vscode.window.showInformationMessage(output || "CodeSense returned no explanation.", { modal: true });
  }));
}
export function deactivate() {}

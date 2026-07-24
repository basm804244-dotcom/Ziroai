'use client';

import { useState } from 'react';
import Editor from '@monaco-editor/react';
import { FileCode, Folder, Play, Save, Plus, Trash2, Terminal } from 'lucide-react';

const FILES = [
  { id: '1', name: 'main.py', language: 'python', content: '# Welcome to AetherAI Workspace\n\ndef main():\n    print("Hello, AetherAI!")\n\nif __name__ == "__main__":\n    main()' },
  { id: '2', name: 'app.js', language: 'javascript', content: '// AetherAI Workspace\n\nconst app = () => {\n  console.log("Hello, AetherAI!");\n};\n\napp();' },
  { id: '3', name: 'README.md', language: 'markdown', content: '# My Project\n\nThis is my workspace in AetherAI.' },
];

export function WorkspaceIDE() {
  const [files, setFiles] = useState(FILES);
  const [activeFile, setActiveFile] = useState(FILES[0]);
  const [terminalOutput, setTerminalOutput] = useState('');
  const [showTerminal, setShowTerminal] = useState(true);

  const runCode = () => {
    setTerminalOutput(`$ python ${activeFile.name}\n> Running...\n> Hello, AetherAI!\n> Execution completed in 0.23s`);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="h-12 bg-gray-900 border-b border-gray-800 flex items-center px-4 space-x-3">
        <button className="text-gray-400 hover:text-white"><Plus className="w-4 h-4" /></button>
        <button className="text-gray-400 hover:text-white"><Folder className="w-4 h-4" /></button>
        <button onClick={runCode} className="text-green-400 hover:text-green-300 flex items-center space-x-1"><Play className="w-4 h-4" /><span className="text-sm">Run</span></button>
        <button className="text-blue-400 hover:text-blue-300 flex items-center space-x-1"><Save className="w-4 h-4" /><span className="text-sm">Save</span></button>
        <button onClick={() => setShowTerminal(!showTerminal)} className={`flex items-center space-x-1 ${showTerminal ? 'text-white' : 'text-gray-400'}`}><Terminal className="w-4 h-4" /><span className="text-sm">Terminal</span></button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-56 bg-gray-900 border-r border-gray-800 overflow-auto">
          <div className="p-3">
            <h3 className="text-xs font-medium text-gray-500 uppercase mb-2">Explorer</h3>
            {files.map((file) => (
              <button key={file.id} onClick={() => setActiveFile(file)} className={`w-full flex items-center space-x-2 px-2 py-1.5 rounded text-sm ${activeFile.id === file.id ? 'bg-blue-500/20 text-blue-400' : 'text-gray-300 hover:bg-gray-800'}`}>
                <FileCode className="w-4 h-4" /><span className="truncate">{file.name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 flex flex-col">
          <div className={`${showTerminal ? 'flex-1' : 'h-full'}`}>
            <Editor height="100%" language={activeFile.language} value={activeFile.content} theme="vs-dark" options={{ minimap: { enabled: false }, fontSize: 14, wordWrap: 'on' }} />
          </div>
          {showTerminal && (
            <div className="h-48 bg-gray-950 border-t border-gray-800 p-4 font-mono text-sm overflow-auto">
              <div className="flex items-center justify-between mb-2"><span className="text-gray-500 text-xs">Terminal</span><button onClick={() => setTerminalOutput('')} className="text-gray-500 hover:text-white text-xs">Clear</button></div>
              <pre className="text-green-400 whitespace-pre-wrap">{terminalOutput || 'Ready...'}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

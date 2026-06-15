import os
import json

def generate():
    md_path = "ARCHITECTURE.md"
    html_path = "architecture_preview.html"
    
    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found.")
        return
        
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    # Escape markdown content for embedding into JS template literal
    escaped_markdown = json.dumps(markdown_content)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Intellicheck - System Architecture</title>
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <!-- Marked.js for Markdown parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    
    <!-- Mermaid.js for Diagrams -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    
    <style>
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #0b0f19;
            color: #f3f4f6;
        }}
        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Outfit', sans-serif;
        }}
        code, pre {{
            font-family: 'JetBrains Mono', monospace;
        }}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #0f172a;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #334155;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #475569;
        }}
        
        /* Markdown rendering styles */
        .prose h1 {{
            color: #f3f4f6;
            font-size: 2.25rem;
            font-weight: 700;
            border-bottom: 1px solid #1f2937;
            padding-bottom: 0.5rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }}
        .prose h2 {{
            color: #f3f4f6;
            font-size: 1.5rem;
            font-weight: 600;
            border-bottom: 1px solid #1f2937;
            padding-bottom: 0.25rem;
            margin-top: 2.5rem;
            margin-bottom: 1rem;
        }}
        .prose h3 {{
            color: #e5e7eb;
            font-size: 1.25rem;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
        }}
        .prose p {{
            margin-bottom: 1rem;
            line-height: 1.75;
            color: #9ca3af;
        }}
        .prose ul, .prose ol {{
            margin-left: 1.5rem;
            margin-bottom: 1rem;
            list-style-type: cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .prose ul {{
            list-style-type: disc;
        }}
        .prose li {{
            margin-bottom: 0.25rem;
            color: #9ca3af;
        }}
        .prose table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            background-color: #0f172a;
            border-radius: 0.5rem;
            overflow: hidden;
            border: 1px solid #1e293b;
        }}
        .prose th {{
            background-color: #1e293b;
            color: #f3f4f6;
            text-align: left;
            padding: 0.75rem 1rem;
            font-weight: 600;
            font-size: 0.875rem;
        }}
        .prose td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #1e293b;
            color: #cbd5e1;
            font-size: 0.875rem;
        }}
        .prose tr:last-child td {{
            border-bottom: none;
        }}
        .prose blockquote {{
            border-left: 4px solid #3b82f6;
            background-color: #1e293b50;
            padding: 0.75rem 1rem;
            margin: 1rem 0;
            border-radius: 0 0.375rem 0.375rem 0;
        }}
        .prose blockquote p {{
            margin-bottom: 0;
            color: #93c5fd;
            font-style: italic;
        }}
        .prose code {{
            background-color: #1e293b;
            color: #f43f5e;
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
        }}
        .prose pre {{
            background-color: #0f172a;
            border: 1px solid #1e293b;
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            margin: 1rem 0;
        }}
        .prose pre code {{
            background-color: transparent;
            color: #e2e8f0;
            padding: 0;
            border-radius: 0;
            font-size: 0.875rem;
        }}
        .prose hr {{
            border-color: #1e293b;
            margin: 2.5rem 0;
        }}
        
        /* Mermaid styling */
        .mermaid-container {{
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 0.75rem;
            padding: 1.5rem;
            margin: 1.5rem 0;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        .mermaid {{
            background-color: transparent !important;
            width: 100%;
        }}
    </style>
</head>
<body class="min-h-screen flex flex-col md:flex-row">

    <!-- Sidebar Navigation -->
    <aside class="w-full md:w-80 bg-[#0f172a] border-r border-[#1e293b] p-6 flex flex-col shrink-0">
        <div class="flex items-center space-x-3 mb-8">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center font-bold text-white text-lg">I</div>
            <div>
                <h1 class="text-white font-bold leading-none text-lg">Intellicheck</h1>
                <span class="text-xs text-slate-400 font-medium">Architecture Portal</span>
            </div>
        </div>
        
        <nav class="flex-1 overflow-y-auto space-y-1 pr-2" id="toc-nav">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Sections</p>
            <!-- Generated dynamically -->
        </nav>
        
        <div class="mt-auto pt-6 border-t border-slate-800 text-xs text-slate-500 flex flex-col gap-1">
            <p>Generated for Sakshi</p>
            <p>Intellicheck Document Verification</p>
        </div>
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 overflow-y-auto px-6 py-12 md:px-16 lg:px-24">
        <article class="max-w-4xl mx-auto prose" id="markdown-container">
            <!-- Rendered Markdown goes here -->
        </article>
    </main>

    <script>
        // Load embedded markdown content
        const markdown = {escaped_markdown};

        // Initialize Mermaid config
        mermaid.initialize({{
            startOnLoad: false,
            theme: 'dark',
            securityLevel: 'loose',
            themeVariables: {{
                background: 'transparent',
                primaryColor: '#1e293b',
                primaryTextColor: '#f3f4f6',
                primaryBorderColor: '#334155',
                lineColor: '#64748b',
                secondaryColor: '#0f172a',
                tertiaryColor: '#1e1b4b'
            }}
        }});

        function escapeHtml(value) {{
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }}

        // Custom renderer for marked.js to intercept code blocks and detect mermaid.
        // Marked changed renderer.code from positional args to a token object, so support both.
        const renderer = new marked.Renderer();
        const originalCodeRenderer = renderer.code;
        
        renderer.code = function(codeOrToken, language, escaped) {{
            const tokenMode = typeof codeOrToken === 'object' && codeOrToken !== null;
            const code = tokenMode ? codeOrToken.text : codeOrToken;
            const lang = tokenMode ? codeOrToken.lang : language;
            const normalizedLang = String(lang || '').trim().split(/\\s+/)[0].toLowerCase();

            if (normalizedLang === 'mermaid') {{
                return `<div class="mermaid-container"><pre class="mermaid">${{escapeHtml(code)}}</pre></div>`;
            }}

            if (typeof originalCodeRenderer === 'function') {{
                return tokenMode
                    ? originalCodeRenderer.call(this, codeOrToken)
                    : originalCodeRenderer.call(this, codeOrToken, language, escaped);
            }}

            return `<pre><code>${{escapeHtml(code)}}</code></pre>`;
        }};

        marked.setOptions({{
            renderer: renderer,
            gfm: true,
            breaks: true
        }});

        // Parse and render the Markdown
        const html = marked.parse(markdown);
        document.getElementById('markdown-container').innerHTML = html;

        // Populate Table of Contents in the Sidebar
        const tocNav = document.getElementById('toc-nav');
        const headings = document.querySelectorAll('#markdown-container h2, #markdown-container h3');
        
        headings.forEach((heading, idx) => {{
            const id = 'section-' + idx;
            heading.id = id;
            
            const link = document.createElement('a');
            link.href = '#' + id;
            link.innerText = heading.innerText;
            
            if (heading.tagName === 'H2') {{
                link.className = "block px-3 py-2 text-sm font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-800 transition-colors";
            }} else {{
                link.className = "block pl-6 pr-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:underline transition-colors";
            }}
            
            tocNav.appendChild(link);
        }});

        // Render Mermaid diagrams
        async function renderMermaidDiagrams() {{
            const diagrams = document.querySelectorAll('.mermaid');

            try {{
                if (typeof mermaid.run === 'function') {{
                    await mermaid.run({{ nodes: diagrams }});
                }} else {{
                    mermaid.init(undefined, diagrams);
                }}
            }} catch (error) {{
                console.error('Mermaid render failed:', error);
            }}
        }}

        renderMermaidDiagrams();
    </script>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Success! Generated {html_path} containing beautiful rendered architecture with diagrams.")

if __name__ == "__main__":
    generate()

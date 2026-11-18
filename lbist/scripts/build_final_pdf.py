"""Convert the final Markdown report to a portable LaTeX/PDF document.

Uses installed pdflatex only; package installation/network access is disabled.
The Markdown remains authoritative if local LaTeX packages are unavailable.
"""
from pathlib import Path
import re,shutil,subprocess,os
R=Path(__file__).resolve().parents[2];O=R/'Results/Final'
def esc(text):
    replacements={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}',
                  '→':r'$\rightarrow$','×':r'$\times$','−':'-','–':'--','—':'---','…':r'\ldots{}','±':r'$\pm$','≤':r'$\leq$','≥':r'$\geq$','°':r'$^\circ$','’':"'",'“':'``','”':"''"}
    return ''.join(replacements.get(c,c) for c in text)
def inline(text):
    parts=re.split(r'(`[^`]+`|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*)',text)
    out=[]
    for p in parts:
        if p.startswith('`'):out.append(r'\texttt{'+esc(p[1:-1])+'}')
        elif p.startswith('**'):out.append(r'\textbf{'+esc(p[2:-2])+'}')
        elif p.startswith('['):
            m=re.fullmatch(r'\[([^]]+)\]\(([^)]+)\)',p)
            if m:out.append(r'\href{'+m[2].replace('%',r'\%')+'}{'+esc(m[1])+'}')
            else:out.append(esc(p))
        else:out.append(esc(p))
    return ''.join(out)
def main():
    lines=(O/'Final_Report.md').read_text(encoding='utf-8').splitlines();body=[];i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('# '):body.append(r'\title{'+inline(line[2:])+r'}\author{VL405 Project Submission}\date{}\maketitle\tableofcontents\clearpage')
        elif line.startswith('## '):body.append(r'\section{'+inline(re.sub(r'^\d+\.\s*','',line[3:]))+ '}')
        elif line.startswith('### '):body.append(r'\subsection{'+inline(line[4:])+ '}')
        elif line.startswith('| '):
            matrix=[]
            while i<len(lines) and lines[i].startswith('| '):
                row=[v.strip() for v in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',v) for v in row):matrix.append(row)
                i+=1
            i-=1
            body.append(r'\begin{center}\resizebox{\textwidth}{!}{\begin{tabular}{'+'l'*len(matrix[0])+'}\\hline\n')
            for j,row in enumerate(matrix):body.append(' & '.join((r'\textbf{'+inline(v)+'}') if j==0 else inline(v) for v in row)+r' \\'+ ('\\hline' if j==0 else ''))
            body.append(r'\hline\end{tabular}}\end{center}')
        elif line.startswith('!['):
            m=re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)',line);image=O/m[2]
            if image.suffix=='.svg':image=image.with_suffix('.png')
            pdf=image.with_suffix('.pdf')
            if pdf.exists():image=pdf
            if image.exists():body.append(r'\begin{figure}[htbp]\centering\includegraphics[width=\textwidth,height=.67\textheight,keepaspectratio]{'+image.relative_to(O).as_posix()+r'}\caption{'+esc(m[1])+r'}\end{figure}')
        elif line:body.append(inline(line)+'\n')
        else:body.append('\n')
        i+=1
    tex=r'''\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\IfFileExists{glyphtounicode.tex}{\input{glyphtounicode.tex}}{}
\pdfgentounicode=1
\usepackage[margin=22mm]{geometry}
\usepackage{graphicx}
\usepackage[hidelinks]{hyperref}
\usepackage{url}
\setlength{\emergencystretch}{4em}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\begin{document}
'''+ '\n'.join(body)+r'\end{document}'
    (O/'Final_Report.tex').write_text(tex,encoding='utf-8')
    tool=shutil.which('pdflatex')
    if not tool:
        candidate=Path(os.environ['LOCALAPPDATA'])/'Programs/MiKTeX/miktex/bin/x64/pdflatex.exe'
        tool=str(candidate) if candidate.exists() else None
    if not tool:
        (O/'pdf_build_status.txt').write_text('PDF unavailable: pdflatex not installed. Markdown and LaTeX supplied.\n');return
    work=O/'work/pdf';work.mkdir(parents=True,exist_ok=True)
    command=[tool,'--disable-installer','-interaction=nonstopmode','-halt-on-error','-output-directory='+str(work),'Final_Report.tex']
    result=None
    with (O/'pdf_build.log').open('w',encoding='utf-8') as log:
        for _ in range(2):
            result=subprocess.run(command,cwd=O,stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:break
    if result.returncode==0 and (work/'Final_Report.pdf').exists():
        shutil.copy2(work/'Final_Report.pdf',O/'Final_Report.pdf')
        (O/'pdf_build_status.txt').write_text('PASS: two local pdflatex passes; no network/package installation.\n')
    else:(O/'pdf_build_status.txt').write_text('PDF build failed; see pdf_build.log. Markdown and LaTeX remain complete.\n')
    print((O/'pdf_build_status.txt').read_text())
if __name__=='__main__':main()

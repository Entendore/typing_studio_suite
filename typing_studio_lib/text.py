"""Language definitions and tokenizer."""
from __future__ import annotations
from typing import Dict, List, Tuple
import re, threading

_LANG_DATA: Dict[str, dict] = {
    "Python": {"keywords": {"False","None","True","and","as","assert","async","await","break","class","continue","def","del","elif","else","except","finally","for","from","global","if","import","in","is","lambda","nonlocal","not","or","pass","raise","return","try","while","with","yield"}, "builtins": {"print","len","range","int","str","float","list","dict","set","tuple","bool","type","isinstance","enumerate","zip","map","filter","sorted","reversed","open","super","property","staticmethod","classmethod","abs","max","min","sum","any","all","hash","id","input","format","hex","oct","bin","round","pow","divmod","chr","ord","repr","vars","dir","getattr","setattr","hasattr","delattr","callable","iter","next"}, "extra_patterns": [("decorator", r"@\w+(\.\w+)*"), ("fstring", r"\b(?:f|r|b|fr|rf|br|rb)(?:\"\"\"[\s\S]*?\"\"\"|\'\'\'[\s\S]*?\'\'\'|\"(?:[^\"\\]|\\.)*\"|\'(?:[^\'\\]|\\.)*\')")], "comment": r"#[^\n]*", "string": r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', "number": r"\b\d+\.?\d*(?:e[+-]?\d+)?\b|0x[0-9a-fA-F]+\b|0b[01]+\b|0o[0-7]+\b"},
    "JavaScript": {"keywords": {"break","case","catch","class","const","continue","debugger","default","delete","do","else","export","extends","finally","for","function","if","import","in","instanceof","let","new","of","return","static","super","switch","this","throw","try","typeof","var","void","while","with","yield","async","await","from","as","null","undefined"}, "builtins": {"console","Math","JSON","Array","Object","String","Number","Boolean","Date","RegExp","Error","Map","Set","Promise","Symbol","Proxy","Reflect","parseInt","parseFloat","isNaN","isFinite","encodeURI","decodeURI","setTimeout","setInterval","clearTimeout","clearInterval","fetch","document","window","require","module","process","Buffer","true","false"}, "extra_patterns": [], "comment": r"//[^\n]*|/\*[\s\S]*?\*/", "string": r'`(?:[^`\\]|\\.)*`|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', "number": r"\b\d+\.?\d*(?:e[+-]?\d+)?\b|0x[0-9a-fA-F]+\b|0b[01]+\b|0o[0-7]+\b"},
    "TypeScript": "JavaScript",
    "CFamily": {"keywords": {"auto","break","case","char","const","continue","default","do","double","else","enum","extern","float","for","goto","if","inline","int","long","register","return","short","signed","sizeof","static","struct","switch","typedef","union","unsigned","void","volatile","while","class","namespace","template","typename","public","private","protected","virtual","override","final","new","delete","try","catch","throw","using","true","false","nullptr","boolean","byte","extends","implements","import","instanceof","interface","native","package","super","synchronized","this","throws","transient","abstract","assert"}, "builtins": {"printf","scanf","malloc","free","sizeof","strlen","std","cout","cin","endl","string","vector","map","set","println","System","Math"}, "extra_patterns": [("preprocessor", r"^\s*#[^\n]*")], "comment": r"//[^\n]*|/\*[\s\S]*?\*/", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "number": r"\b\d+\.?\d*(?:e[+-]?\d+)?\b|0x[0-9a-fA-F]+\b|0b[01]+\b"},
    "CSharp": {"keywords": {"abstract","as","base","bool","break","byte","case","catch","char","checked","class","const","continue","decimal","default","delegate","do","double","else","enum","event","explicit","extern","false","finally","fixed","float","for","foreach","goto","if","implicit","in","int","interface","internal","is","lock","long","namespace","new","null","object","operator","out","override","params","private","protected","public","readonly","ref","return","sbyte","sealed","short","sizeof","stackalloc","static","string","struct","switch","this","throw","true","try","typeof","uint","ulong","unchecked","unsafe","ushort","using","virtual","void","volatile","while","async","await","yield","var","dynamic","get","set","value","nameof","when","where","global","record","init"}, "builtins": {"Console","Math","Convert","String","Array","List","Dictionary","HashSet","Task","Thread","Exception","InvalidOperationException","DateTime","TimeSpan","Guid","StringBuilder","Random","Regex","IEnumerable","IEnumerator","IDisposable","Action","Func","Tuple"}, "extra_patterns": [("preprocessor", r"^\s*#[^\n]*"), ("decorator", r"\[[\w\s,\.()=]*\]")], "comment": r"//[^\n]*|/\*[\s\S]*?\*/", "string": r'\$?@"[^"]*"|@"[^"]*"|"(?:[^"\\]|\\.)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "number": r"\b\d+\.?\d*[fFdDmM]?\b|0x[0-9a-fA-F]+\b|0b[01]+\b"},
    "Java": {"keywords": {"abstract","assert","boolean","break","byte","case","catch","char","class","const","continue","default","do","double","else","enum","extends","final","finally","float","for","goto","if","implements","import","instanceof","int","interface","long","native","new","package","private","protected","public","return","short","static","strictfp","super","switch","synchronized","this","throw","throws","transient","try","void","volatile","while","true","false","null","var","record","yield","sealed","permits","non-sealed"}, "builtins": {"System","Math","String","Integer","Double","Float","Long","Boolean","Character","Object","Class","Void","Exception","RuntimeException","ArrayList","LinkedList","HashMap","HashSet","TreeMap","TreeSet","Array","Arrays","Collections","List","Map","Set","Queue","Deque","Thread","Runnable","Callable","Future","Optional","Stream","Scanner","PrintWriter","BufferedReader","BufferedWriter"}, "extra_patterns": [("decorator", r"@\w+(\.\w+)*")], "comment": r"//[^\n]*|/\*[\s\S]*?\*/", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "number": r"\b\d+\.?\d*(?:e[+-]?\d+)?[fFdDlL]?\b|0x[0-9a-fA-F]+\b|0b[01]+\b"},
    "Go": {"keywords": {"break","case","chan","const","continue","default","defer","else","fallthrough","for","func","go","goto","if","import","interface","map","package","range","return","select","struct","switch","type","var","nil","true","false","iota"}, "builtins": {"fmt","os","io","strings","strconv","math","time","len","cap","make","new","append","copy","delete","panic","recover","print","println","true","false","nil","iota"}, "extra_patterns": [], "comment": r"//[^\n]*|/\*[\s\S]*?\*/", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|`[^`]*`', "number": r"\b\d+\.?\d*(?:e[+-]?\d+)?\b|0x[0-9a-fA-F]+\b|0b[01]+\b|0o[0-7]+\b"},
    "Rust": {"keywords": {"fn","let","mut","const","static","if","else","for","while","loop","match","return","break","continue","in","as","use","mod","pub","struct","enum","trait","impl","where","self","Self","super","crate","extern","ref","move","async","await","dyn","unsafe","true","false"}, "builtins": {"println","print","format","vec","String","Vec","Option","Result","Box","Rc","Arc","Some","None","Ok","Err","HashMap","BTreeMap","HashSet"}, "extra_patterns": [("macro", r"\b([a-zA-Z_]\w*)!"), ("lifetime", r"\'\w+")], "comment": r"//[^\n]*|/\*[\s\S]*?\*/", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "number": r"\b\d+\.?\d*(?:e[+-]?\d+)?\b|0x[0-9a-fA-F]+\b|0b[01]+\b|0o[0-7]+\b"},
    "Ruby": {"keywords": {"def","end","if","elsif","else","unless","while","until","for","do","break","next","redo","retry","return","class","module","begin","rescue","ensure","raise","yield","self","super","nil","true","false","and","or","not","alias","attr_accessor","attr_reader","attr_writer","require","require_relative","include","extend","private","public","protected","defined?","BEGIN","END","__FILE__","__LINE__"}, "builtins": {"puts","print","p","pp","require","require_relative","include","attr_accessor","attr_reader","attr_writer","Integer","Float","String","Array","Hash","Object","Module","Class","Range","Regexp","Proc","lambda","binding","caller","catch","throw","loop","sleep","exit","abort","at_exit","fork","spawn","system","exec","open","File","Dir","IO","Socket","Thread","Mutex","ENV","ARGV","STDIN","STDOUT","STDERR"}, "extra_patterns": [("symbol", r":[a-zA-Z_]\w*"), ("variable", r"@@?[a-zA-Z_]\w*")], "comment": r"#[^\n]*", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|:[a-zA-Z_]\w*', "number": r"\b\d+\.?\d*(?:e[+-]?\d+)?\b|0x[0-9a-fA-F]+\b|0b[01]+\b|0o[0-7]+\b"},
    "PHP": {"keywords": {"abstract","and","array","as","break","callable","case","catch","class","clone","const","continue","declare","default","do","echo","else","elseif","empty","enddeclare","endfor","endforeach","endif","endswitch","endwhile","extends","final","finally","fn","for","foreach","function","global","goto","if","implements","include","include_once","instanceof","insteadof","interface","isset","list","namespace","new","or","print","private","protected","public","require","require_once","return","static","switch","throw","trait","try","unset","use","var","while","xor","yield","true","false","null"}, "builtins": {"echo","print","array","isset","unset","include","require","strlen","strpos","str_replace","substr","count","sort","explode","implode","date","time","json_encode","json_decode","file_get_contents","file_put_contents","fopen","fclose","fread","fwrite","mysql_query","mysqli_query","PDO","session_start","$_GET","$_POST","$_SESSION","$_COOKIE","$_SERVER","$_REQUEST","$_FILES","$_ENV"}, "extra_patterns": [("variable", r"\$\w+")], "comment": r"//[^\n]*|/\*[\s\S]*?\*/|#[^\n]*", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "number": r"\b\d+\.?\d*(?:e[+-]?\d+)?\b|0x[0-9a-fA-F]+\b|0b[01]+\b"},
    "HTML": {"keywords": set(), "builtins": set(), "extra_patterns": [("tag", r"</?(\w+)"), ("attr", r"\b([a-zA-Z-]+)(?==)")], "comment": r"<!--[\s\S]*?-->", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "number": r"\b\d+\.?\d*\b"},
    "CSS": {"keywords": set(), "builtins": set(), "extra_patterns": [("selector", r"[#.]?[\w-]+(?=\s*\{)"), ("property", r"\b[\w-]+(?=\s*:)"), ("hex_color", r"#[0-9a-fA-F]{3,8}\b"), ("variable", r"--[\w-]+")], "comment": r"/\*[\s\S]*?\*/", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "number": r"\b\d+\.?\d*(?:px|em|rem|vw|vh|%|s|ms|deg|fr|pt|pc|in|cm|mm)?\b"},
    "SQL": {"keywords": {"SELECT","FROM","WHERE","INSERT","INTO","VALUES","UPDATE","SET","DELETE","CREATE","TABLE","ALTER","DROP","INDEX","VIEW","JOIN","INNER","LEFT","RIGHT","OUTER","ON","GROUP","BY","HAVING","ORDER","ASC","DESC","LIMIT","OFFSET","DISTINCT","UNION","ALL","AS","AND","OR","NOT","IN","EXISTS","BETWEEN","LIKE","IS","NULL","PRIMARY","KEY","FOREIGN","REFERENCES","UNIQUE","DEFAULT","CHECK","CONSTRAINT","BEGIN","COMMIT","ROLLBACK","TRANSACTION","CASE","WHEN","THEN","ELSE","END"}, "builtins": {"COUNT","SUM","AVG","MIN","MAX","CONCAT","SUBSTRING","UPPER","LOWER","LENGTH","TRIM","ROUND","NOW","DATE","TIME","TIMESTAMP","VARCHAR","INT","INTEGER","FLOAT","DOUBLE","BOOLEAN","TEXT","BLOB"}, "extra_patterns": [], "comment": r"--[^\n]*|/\*[\s\S]*?\*/", "string": r"'[^'\\]*(?:\\.[^'\\]*)*'", "number": r"\b\d+\.?\d*\b"},
    "Bash": {"keywords": {"if","then","else","elif","fi","for","do","done","while","until","case","esac","function","in","return","break","continue","exit","local","export","readonly","unset","shift","source","alias"}, "builtins": {"echo","printf","read","set","trap","kill","jobs","bg","fg","wait","cd","pwd","ls","mkdir","rmdir","rm","cp","mv","cat","grep","awk","sed","find","xargs","which","whoami","hostname","date","sleep"}, "extra_patterns": [("variable", r"\$\w+|\$\{[^}]+\}")], "comment": r"#[^\n]*", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "number": r"\b\d+\.?\d*\b"},
    "JSON": {"keywords": set(), "builtins": set(), "extra_patterns": [("property", r'"([^"\\]|\\.)*"(?=\s*:)')], "comment": r"//[^\n]*", "string": r'"([^"\\]|\\.)*"', "number": r"\b-?\d+\.?\d*(?:e[+-]?\d+)?\b"},
    "YAML": {"keywords": set(), "builtins": set(), "extra_patterns": [("property", r"\b[\w-]+(?=\s*:)")], "comment": r"#[^\n]*", "string": r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "number": r"\b-?\d+\.?\d*\b"},
    "Markdown": {"keywords": set(), "builtins": set(), "extra_patterns": [("heading", r"^#{1,6}[^\n]*"), ("bold", r"\*\*[\s\S]*?\*\*|__[\s\S]*?__"), ("italic", r"\*[\s\S]*?\*|_[\s\S]*_"), ("code", r"```[\s\S]*?```|`[^`\n]*`"), ("link", r"\[([^\]]+)\]\(([^)]+)\)")], "comment": r"", "string": r"", "number": r""},
    "Text": {"keywords": set(), "builtins": set(), "extra_patterns": [], "comment": r"", "string": r"", "number": r""},
}

for _k, _v in list(_LANG_DATA.items()):
    if isinstance(_v, str) and _v in _LANG_DATA:
        _LANG_DATA[_k] = _LANG_DATA[_v]

class Tokenizer:
    _COMPILED: Dict[str, re.Pattern] = {}
    _LOCK = threading.Lock()

    @classmethod
    def _compile(cls, lang: str) -> re.Pattern:
        if lang not in cls._COMPILED:
            with cls._LOCK:
                if lang not in cls._COMPILED:
                    data = _LANG_DATA.get(lang, _LANG_DATA["Text"])
                    patterns = list(data.get("extra_patterns", []))
                    if data.get("comment"): patterns.append(("comment", data["comment"]))
                    if data.get("string"): patterns.append(("string", data["string"]))
                    if data.get("number"): patterns.append(("number", data["number"]))
                    if data.get("keywords"):
                        patterns.append(("keyword", r"\b(?:" + "|".join(data["keywords"]) + r")\b"))
                    if data.get("builtins"):
                        patterns.append(("builtin", r"\b(?:" + "|".join(data["builtins"]) + r")\b"))
                    patterns.extend([
                        ("boolean", r"\b(?:true|false|null|True|False|None|nil|undefined)\b"),
                        ("constant", r"\b[A-Z_][A-Z0-9_]+\b"),
                        ("function", r"\b([a-zA-Z_]\w*)\s*(?=\()"),
                        ("class_name", r"\b([A-Z]\w*)\b"),
                        ("identifier", r"\b[a-zA-Z_]\w*\b"),
                        ("operator", r"[+\-*/%=<>!&|^~]+"),
                        ("bracket", r"[(){}\[\]]"),
                        ("punctuation", r"[;:,.]"),
                        ("whitespace", r"\s+"),
                        ("other", r".")
                    ])
                    valid = [(n, p) for n, p in patterns if p]
                    pat_str = "|".join(f"(?P<{n}>{p})" for n, p in valid)
                    cls._COMPILED[lang] = re.compile(pat_str, re.MULTILINE | re.DOTALL)
        return cls._COMPILED[lang]

    @classmethod
    def tokenize(cls, text: str, lang: str) -> List[Tuple[str, str]]:
        compiled = cls._COMPILED.get(lang) or cls._compile(lang)
        return [(m.lastgroup, m.group()) for m in compiled.finditer(text)]

    @classmethod
    def find_structural_markers(cls, text: str, lang: str) -> List[Tuple[int, str, str]]:
        markers = []
        pos = 0
        for tt, tx in cls.tokenize(text, lang):
            if tt == "keyword" and tx in ("def", "class", "func", "fn"):
                nc = text[pos + len(tx):pos + len(tx) + 80]
                m = re.match(r"\s+(\w+)", nc)
                if m:
                    nm = m.group(1)
                    kind = "class" if tx in ("class",) else "def"
                    markers.append((pos, kind, f"{tx} {nm}{'()' if kind != 'class' else ''}"))
            elif tt == "comment":
                s = tx.strip()
                if s.startswith("/*") and s.endswith("*/"): s = s[2:-2].strip()
                elif s.startswith("//"): s = s[2:].strip()
                elif s.startswith("#"): s = s[1:].strip()
                elif s.startswith("--"): s = s[2:].strip()
                if (5 <= len(s) <= 120 and not s.startswith("!") and not s.startswith("encoding") and
                    not s.startswith("coding") and not s.startswith("type:") and
                    not s.startswith("noqa") and not s.startswith("pragma") and not s.startswith("pylint")):
                    markers.append((pos, "section", s))
            pos += len(tx)
        return markers

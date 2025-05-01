from pathlib import Path
from typing import List, Dict, Set, Optional
import re

class LeanFileNode:
    def __init__(self, filePath: Path):
        """
        Node based on .lean file
        
        param:
            filePath: Path of .lean file 
        """
        self.rawPath = filePath
        self.branch: str
        self.group: str
        self.prevNode: Set[str] = set()
        self.nextNode: Set[str] = set()
        self.depends: List[str] = []

        self.position: List[float, float]
        self.color: str = '#303030'
        self.radius: float
        self.contents = {
            'def': 0,
            'theorem': 0,
            'lemma': 0,
            'axiom': 0,
        }
        
        # init
        self._parse_file()
    
    def _parse_file(self):
        """Parse file"""
        # Classify
        filePath = self.rawPath
        if filePath.suffix != ".lean":
            raise('Invaild File Path')
        filePath = filePath.with_suffix('')
        parts = list(filePath.parts)
        lower = [part.lower() for part in parts]
        split = 'mathlib'
        if split in lower:
            index = lower.index(split)
            branch = str(Path(*parts[index + 1:])).replace('/', '.')
            self.branch = branch.replace('\\', '.')
            self.group = parts[index + 1]
        else:
            self.branch = ''
            self.group = ''
            raise('Invaild File Path')
        
        # Read content
        with open(self.rawPath, 'r', encoding='utf-8') as f:
            filetext = f.read()
            
            filetext = re.sub(r'\/-.*?-\/', '', filetext, flags=re.DOTALL)
            filetext = re.sub(r'--.*$', '', filetext, flags=re.MULTILINE)
            
            # content = f.readlines()
            content = filetext.splitlines()
            startImport, endImport = False, False
            for line in content:
                line = line.strip()
                if line.startswith('import') and not endImport:
                    self.depends.append(self._parse_import(line))
                    startImport = True
                elif startImport and not endImport:
                    endImport = True
                
                for type in self.contents.keys():
                    if line.startswith(type + ' ') or line.startswith('@[' + type + ']'):
                        self.contents[type] += 1
    
    def _parse_import(self, raw: str) -> str:
        """Parse import statement"""
        parts = raw.split()
        if len(parts) < 2:
            return ""
        imported = parts[1]        
        return imported[8:]
    
    def addNode_prev(self, node: str):
        self.prevNode.add(node)
    
    def addNode_next(self, node: str):
        self.nextNode.add(node)
    
    def __repr__(self):
        return f"<LeanFileNode: {self.branch}>"
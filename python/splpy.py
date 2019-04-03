#!/usr/bin/python

import sys
import math
import re

"""
A Shakespeare Compiler written in Python, splc.py
This is a compiler that implements the majority of the Shakespeare programming language
invented by Kalle Hasselstrom and Jon Aslund, I take no credit for inventing the language.
This software is relased into the public domain
(c) V1.2 Sam Donow 2013-2015
sad3@williams.edu
drsam94@gmail.com
"""

#missing features

#full support for multi-word nouns/names

pos_adj    = []
neg_adj    = []
pos_comp   = []
neg_comp   = []
pos_nouns  = []
neg_nouns  = []
valid_names= []
zero_nouns = ['nothing', 'zero']
src        = ""
N          = 0
vartable   = set([])
speaker    = ""
target     = ""
stage      = set([])
actnum     = 0
act_names  = {}
scene_names= []

python_program = ''

#report a compile-time error, then exit
def Assert(b, s):
    global N
    if not b:
        sys.stderr.write(s + " at line " + str(N) + "\n")
        sys.exit(1)

#Abstraction for writing to file, eased python 2/3 agnosticity,
#and will eventually allow file output instead of stdout if that
#ever is desired
def writeToFile(s):
    #sys.stdout.write(str(s) + "\n")
    global python_program
    python_program = python_program + str(s) + "\n"

def isNoun(word):
    return word in pos_nouns or word in neg_nouns or word in zero_nouns

def isAdjective(word):
    return word in pos_adj or word in neg_adj

def isComparative(word):
    return word in pos_comp or word in neg_comp

#returns 1 for "nice" and neutral nouns, -1 for nasty ones
def nounValue(word):
    Assert(isNoun(word), "Tried to find the nounvalue of a non-noun")
    return 1 if word in pos_nouns else -1 if word in neg_nouns else 0

#return s with all whitespace characters removed
def trimWhitespace(s):
    trimmed = ""
    for c in s:
        if c not in ['\t', '\r', '\n', ' ']:
            trimmed += c
    return trimmed

#return s with all whitespace characters before the first non-whitedspace character removed
def trimLeadingWhitespace(s):
    trimIndex = 0
    for c in s:
        if c in ['\t', '\r', '\n', ' ']:
            trimIndex +=1
        else:
            break
    return s[trimIndex:]

#A whitespace-agnositic beginswith method
def beginsWithNoWhitespace(s, pattern):
    return beginsWith(trimWhitespace(s), pattern)

def beginsWith(s, pattern):
    return s[:len(pattern)] == pattern

def loadFileIntoList(filename, list):
    f = open(filename, 'r')
    for word in f.readlines():
        list.append(word.split(" ")[-1][:-1])
    f.close()
    
def loadFileIntoListCharName(filename, list):
    f = open(filename, 'r')
    for word in f.readlines():
        list.append(("".join(word.split(" ")).lower())[:-1])
    f.close()

#load initial noun and adjective lists
def loadWordLists():
    loadFileIntoList("include/neutral_adjective.wordlist" , pos_adj)
    loadFileIntoList("include/positive_adjective.wordlist", pos_adj)
    loadFileIntoList("include/negative_adjective.wordlist", neg_adj)
    loadFileIntoList("include/positive_noun.wordlist", pos_nouns)
    loadFileIntoList("include/neutral_noun.wordlist" , pos_nouns)
    loadFileIntoList("include/negative_noun.wordlist", neg_nouns)
    loadFileIntoList("include/positive_comparative.wordlist", pos_comp)
    loadFileIntoList("include/negative_comparative.wordlist", neg_comp)
    loadFileIntoListCharName("include/character.wordlist", valid_names)

roman_values = { 'M': 1000, 'D': 500, 'C': 100, 'L': 50, 'X': 10, 'V': 5, 'I': 1 }
def parseRomanNumeral(roman_string):
    roman_string = roman_string.upper()
    strindex = 0
    roman_sum = 0
    while strindex < len(roman_string) - 1:
        if(roman_values[roman_string[strindex]] < roman_values[roman_string[strindex+1]]):
            roman_sum -= roman_values[roman_string[strindex]]
        else:
            roman_sum += roman_values[roman_string[strindex]]
        strindex += 1
    return roman_sum + roman_values[roman_string[strindex]]

def isNumber(s):
    words = s.split(" ")
    for word in words:
        if isNoun(word):
            return True
    return False



#parse a string that is supposed to evaluate to a number
#if failOk is set to true, will return 0 for phrases that do not evaluate to a number
def parseNum(s, failOk = False):
    words = s.split(" ")
    nounIndex = len(words)
    for i in range(0,len(words)):
        if isNoun(words[i]):
            nounIndex = i
            break
    ok = nounIndex < len(words)
    if not ok and failOk:
        return 0
    Assert (ok, str(words) + "\nExpected a number, but found no noun")
    value = nounValue(words[nounIndex])
    for word in words[:nounIndex]:
        if isAdjective(word):
            value *= 2
    return value

def parseEnterOrExit():
    global stage
    endBracket = src[N].find(']')
    Assert(endBracket >= 0, "[ without matching ]")
    enterOrExit = src[N][src[N].find('[')+1:src[N].find(']')]
    if beginsWithNoWhitespace(enterOrExit, "Enter"):
        names = enterOrExit[enterOrExit.find(" ") + 1:].split(" and ")
        for namestr in names:
            name = ("".join(namestr.split(" "))).lower()
            Assert(name in vartable, "Undeclared actor entering a scene")
            stage.add(name)
        Assert(len(stage) < 3, "Too many actors on stage")
    elif beginsWithNoWhitespace(enterOrExit, "Exit"):
        names = enterOrExit[enterOrExit.find(" ") + 1:].split(" and ")
        for namestr in names:
            name = ("".join(namestr.split(" "))).lower()
            Assert(name in stage, "Trying to make an actor who is not in the scene exit")
            stage.remove(name)
    elif beginsWithNoWhitespace(enterOrExit, "Exeunt"):
        stage = set([])
    else:
        Assert(False, "Bracketed clause without Enter, Exit, or Exeunt")

#returns the index of the leftmost punctuation mark in s
def findPunctuation(s):
    valids = []
    for val in [s.find('.'), s.find('!'), s.find('?')]:
        if val >= 0:
            valids.append(val)
    return -1 if len(valids) == 0 else min(valids)

#returns an array of the punctuation-delimited statements at the current location in the parsing
def getStatements():
    global N
    statements = []
    line = trimLeadingWhitespace(src[N])
    unfinished = False
    while line.find(':') < 0 and line.find('[') < 0:
        punctuation = findPunctuation(line)
        if punctuation < 0:
            if unfinished == False:
                statements.append(line[:-1])
            else:
                statements[-1] += line[:-1]
            N += 1
            line = src[N]
            unfinished = True
        elif punctuation > 0:
            if not unfinished:
                statements.append("")
            statements[-1] += line[:punctuation]
            line = line[punctuation + 1:]
            unfinished = False
    retval = []
    for stat in statements:
        if len(trimWhitespace(stat)) > 0:
            retval.append(stat)
    return retval


class Tree:
    def __init__(self, v, l, r):
        self.value = v
        self.left  = l
        self.right = r

def wordToOperator(op):
    if op == "sum":
        return "+"
    elif op == "difference":
        return "-"
    elif op == "quotient":
        return "/"
    elif op == "product":
        return "*"
    else:
        Assert(False, "Illegal Operator")

binop = ["sum", "difference", "quotient", "product"]
unop  = ["square", "cube", "twice"]
def buildExpressionTree(expr):
    #print expr
    Assert (len(expr) > 0, "Ill-formed Expression in " + str(expr))
    if expr[0] == "square":
        if expr[1] == "root":
            op = "isqrt"
            expr = expr[2:]
            num, expr = buildExpressionTree(expr)
            return Tree(op, num, ""), expr
    elif expr[0] == "remainder":
        if expr[1] == "of" and expr[2] == "the" and expr[3] == "quotient":
            expr = expr[4:]
            op = "%"
            left, expr  = buildExpressionTree(expr)
            right, expr = buildExpressionTree(expr)
            return Tree(op, left, right), expr
    if expr[0] in binop:
        op = wordToOperator(expr[0])
        expr  = expr[1:]
        left, expr  = buildExpressionTree(expr)
        right, expr = buildExpressionTree(expr)
        return Tree(op, left, right), expr
    elif expr[0] in unop:
        op = expr[0]
        expr = expr[1:]
        num, expr = buildExpressionTree(expr)
        return Tree(op, num, ""), expr

    if True:
        if expr[0] == "and" or expr[0] == "than":
            i=1
        elif expr[0] == '' and expr[1] == "than":
            i=2
        else:
            i=0
        numstr = ""
        while expr[i] not in binop and expr[i] not in unop and expr[i] not in ["and", "remainder"]:
            #print "".join([expr[j].lower() for j in range(i,min(i+4,len(expr)))])
            #print vartable
            if expr[i] in ["you", "thee", "yourself", "thyself", "thou"]:
                expr = expr[i + 1:]
                return Tree(target+".value", "", ""), expr
            elif expr[i] in ["me", "myself", "i"]:
                expr = expr[i + 1:]
                return Tree(speaker+".value", "", ""), expr
            elif expr[i].lower() in vartable:
                name = expr[i]
                expr = expr[i + 1:]
                #print name,expr
                return Tree(name.lower()+".value", "", ""), expr
            elif "".join([expr[j].lower() for j in range(i,min(i+2,len(expr)))]) in vartable:
                name = "".join([expr[j].lower() for j in range(i,min(i+2,len(expr)))])
                expr = expr[i + 2:]
                #print name
                return Tree(name.lower()+".value", "", ""), expr
            elif "".join([expr[j].lower() for j in range(i,min(i+3,len(expr)))]) in vartable:
                name = "".join([expr[j].lower() for j in range(i,min(i+3,len(expr)))])
                expr = expr[i + 3:]
                #print name
                return Tree(name.lower()+".value", "", ""), expr
            elif "".join([expr[j].lower() for j in range(i,min(i+4,len(expr)))]) in vartable:
                name = "".join([expr[j].lower() for j in range(i,min(i+4,len(expr)))])
                expr = expr[i + 4:]
                #print name
                return Tree(name.lower()+".value", "", ""), expr
            elif i == len(expr) - 1:
                numstr += expr[i]
                i = len(expr)
                #print numstr
                #print isNumber(numstr)
                break
            else:
                numstr += expr[i] + " "
                #print numstr
                i += 1
        if i == len(expr):
            expr = []
        else:
            expr = expr[i:]
        if not isNumber(numstr):
            #print expr
            return buildExpressionTree(expr)
        else:
            return Tree(str(parseNum(numstr)), "", ""), expr

def TreeToString(tree):
    if tree.left == "":
        #just a value
        return str(tree.value)
    elif tree.right == "":
        #unary operator
        return str(tree.value) + "(" + TreeToString(tree.left) + ")"
    else:
        #binary operator
        return "(" + TreeToString(tree.left) + " " + str(tree.value) + " " + TreeToString(tree.right) + ")"

def parseExpr(expr):
    tree = buildExpressionTree(expr.split(" "))[0]
    return TreeToString(tree)

def concatWords(wordArray):
    c = ""
    for word in wordArray:
        c += word
    return c

def firstWord(statment):
    words = statement.split(" ")
    for word in words:
        if len(word) > 0:
            return word

def parseStatement(stat,indentlevel=0):
    leadingWhitespace = (6+indentlevel)*"    "
    statement = trimLeadingWhitespace(stat).lower()
    first = statement.split(" ")[0]
    trimmed = trimWhitespace(statement)
    if first in ["you", "thou"]:
        #this is an assignment of the form Prounoun [as adj as] expression
        expr = ""
        if statement.rfind(" as ") >= 0:
            expr = statement[statement.rfind(" as ") + 4:]
        else:
            expr = statement[len(first) + 1:]
        stringtoreturn = target + ".value = " + parseExpr(expr) + " \n"
    elif first in ["i"]:
        #this is an assignment of the form Prounoun [as adj as] expression
        expr = ""
        if statement.rfind(" as ") >= 0:
            expr = statement[statement.rfind(" as ") + 4:]
        else:
            expr = statement[len(first) + 1:]
        stringtoreturn = speaker + ".value = " + parseExpr(expr) + " \n"
    elif first in ['remember']:
        #push onto stack
        expr = statement[len(first) + 1:]
        stringtoreturn = "{}.push({})\n".format(target,parseExpr(expr))
    elif first in ['recall']:
        #pop from stack
        stringtoreturn = "{}.pop()\n".format(target)
    elif first in ['forget']:
        #dump stack
        stringtoreturn = target + ".stack = [] \n"
    elif trimmed == "openyourheart" or trimmed == "openthyheart":
        #numerical output
        stringtoreturn = "print({}.value,end='')\n".format(target)
    elif trimmed == "speakyourmind" or trimmed == "speakthymind":
        #character output
        stringtoreturn = "print(chr({}.value),end='')\n".format(target)
    elif trimmed == "listentoyourheart" or trimmed == "listentothyheart":
        #numerical input
        stringtoreturn = "{}.value = int(input())\n".format(target)
    elif trimmed == "openyourmind" or trimmed == "openyourmind":
        #character input
        stringtoreturn = target + ".value = ord(getKey())\n"
    elif trimmed == "thedieiscast" or trimmed == "aleaiactaest":
        #random number generator seed, no character specified: Caesar    
        stringtoreturn = "seed(Caesar.value)\n"
    elif beginsWith(statement, "the die is cast by"):
        #random number generator seed, character specified
        location = statement.find("the die is cast by")
        stringtoreturn = "seed(" + parseStatement(statement[location + 19:]) + " )\n"
    elif beginsWith(statement, "let fortune") or beginsWith(statement, "let fate"):
        #random number
        stringtoreturn = target + ".value = randint(0,255)\n"
    elif first in ["am", "are", "art", "be", "is"]:
        #questions - do not yet support "not"
        left  = ""
        kind  = ""
        right = ""
        if statement.find("as") >= 0:
            try:
                left, kind, right = statement.split(" as ")
            except Exception as e:
                sys.stderr.write("Ill-formed statement at Py:356 in {}: {}".format(statement,e))
                sys.exit(1)
            Assert(isAdjective(kind), "Ill-formed conditional (at Py:350) in " + statement)
            kind = "equal"
        elif statement.find("more") >= 0:
            words = statement.split(" ")
            moreloc = 0
            for i in range(0, len(words)):
                if words[i] == "more":
                    moreloc = i
                    break
            Assert(isAdjective(words[moreloc + 1]), "Ill-formed conditional (at Py:359) in " + statement)
            kind = "greater" if words[moreloc + 1] in pos_adj else "lesser"
            left, right = statement.split(" more " + words[moreloc + 1] + " ")
        else:
            comp = ""
            for word in statement.split(" "):
                if isComparative(word):
                    comp = word
                    break
            Assert(len(comp) > 0, "Ill-formed conditional (at Py:368) in " + statement)
            kind = "greater" if comp in pos_comp else "lesser"
            left, right = statement.split(comp)
        stringtoreturn = "condition = (" + parseExpr(left) + ") " + (">" if kind == "greater" else "<" if kind == "lesser" else "==") + " (" + parseExpr(right) + ")\n"
    elif beginsWith(statement, "if so,"):
        #positive condition
        location = statement.find("if so,")
        stringtoreturn = "if (condition):\n" + parseStatement(statement[location + 7:],indentlevel=indentlevel+1) + " \n"
    elif beginsWith(statement, "if not,"):
        #negative condition
        location = statement.find("if not,")
        stringtoreturn = "if (not condition):\n" + parseStatement(statement[location + 8:],indentlevel=indentlevel+1) + " \n"
    elif beginsWith(statement, "let us") or beginsWith(statement, "we shall") or beginsWith(statement, "we must"):
        words = statement.split(" ")
        nextTwo = words[2] + " " + words[3]
        Assert (nextTwo == "return to" or nextTwo == "proceed to", "Ill-formed goto")
        # classic goto with scene or act
        if words[4] == "scene" or words[4] == "act":
            if words[4] == "act":
                stringtoreturn = "act = " + str(parseRomanNumeral(words[5])) + '\n'
                stringtoreturn += leadingWhitespace + "raise ActChange('Act {}, Scene {}'.format(act,scene))\n"
            else:
                stringtoreturn = "scene = " + str(parseRomanNumeral(words[5])) + '\n'
                stringtoreturn += leadingWhitespace + "raise SceneChange('Act {}, Scene {}'.format(act,scene))\n"
        else:
            restOfPhrase = concatWords(words[4:])
            type_ = "scene" if restOfPhrase in scene_names[actnum].keys() \
            else "act" if restOfPhrase in act_names.keys() else "none"
            Assert (type_ != "none", "Goto refers to nonexistant act or scene")
            nameDict = act_names if type_ == "act" else scene_names[actnum]
            stringtoreturn = type_+ " = " + str(nameDict[restOfPhrase]) + '\n'
            if type_ == "act":
                stringtoreturn += leadingWhitespace + "raise ActChange('Act {}, Scene {}'.format(act,scene))\n"
            else:
                stringtoreturn += leadingWhitespace + "raise SceneChange('Act {}, Scene {}'.format(act,scene))\n"
    else:
        return "#"
    return leadingWhitespace + stringtoreturn

def writeScenes(scenes, isLast):
    actpreamble = """        if act=={}:
            scene=1
            while 1:
                try:"""
    writeToFile(actpreamble.format(actnum))
    for j in range(0, len(scenes)):
        writeToFile("    "*5+'if scene=={}:'.format(str(j+1)))
        if (scenes[j]!=''):
            #writeToFile("    "*5+'if scene=={}:'.format(str(j+1)))
            writeToFile(scenes[j])
        #else:
        #    writeToFile('pass')
        writeToFile("    "*6+"scene+=1")
        if j >= len(scenes) - 1:
            writeToFile("    "*5+'break')
    writeToFile("    "*4+"except SceneChange as e:\n"+
                #"    "*5+"print('Scene Change: {}'.format(e))\n"+
                "    "*5+"continue\n"+
                "    "*3+"act+=1")


def handleDeclarations():
    global N
    global src
    #variables, declaration syntax:
    #Name, value
    declarations = []
    unfinished = False
    while not beginsWithNoWhitespace(src[N], 'Act'):
        Assert(N < len(src) - 1, "File contains no Acts")
        if len(trimWhitespace(src[N])) > 0:
            if not unfinished:
                declarations.append(src[N])
            else:
                declarations[-1] += src[N]
            unfinished = src[N].find('.') < 0
        N += 1
    
              

    for dec in declarations:
        commaIndex = dec.find(',')
        Assert(commaIndex > 0, "Improper declaration " + str(declarations))
        wordsInName = trimLeadingWhitespace(dec[:commaIndex]).split(" ")
        varname = ("".join(wordsInName)).lower()
        value = parseNum(dec[commaIndex:-2], True)
        writeToFile(str(varname) + " = Character(" + str(value) + ",\"" + str(varname) + "\");")
        #print (varname)
        Assert(varname in valid_names, "Non-Shakespearean variable name")
        vartable.add(varname)

def getActOrSceneNumber(s, actOrScene):
    num = s[s.find(actOrScene):].split(" ")[1]
    if num.find(':') > 0:
        num = num[:num.find(':')]
    else:
        Assert (False, "Bad " + actOrScene + " heading")
    return parseRomanNumeral(num)

def getActOrSceneDescription(s):
    desc = trimWhitespace(s[s.find(':')+1:]).lower()
    p = findPunctuation(desc)
    if p > 0:
        desc = desc[:p]
    return desc

# Gets all the names of scenes and acts, and adds them to the respective tables
# This must be done in a preprocessing step, in order to enable gotos to future acts/scenes
def parseAllActAndSceneDescriptions():
    global scene_names
    global act_names
    current_act = 0
    current_scene = 0
    scene_names = [{}]
    for line in src:
        if beginsWithNoWhitespace(line, "Act"):
            desc = getActOrSceneDescription(line)
            current_act += 1
            act_names[desc] = current_act
            scene_names.append(dict())
            current_scene = 0
        elif beginsWithNoWhitespace(line, "Scene"):
            desc = getActOrSceneDescription(line)
            current_scene += 1
            scene_names[current_act][desc] = current_scene

#-------------------------------Begin Main Program-------------------------#
Assert(len(sys.argv) > 1, "No input file")
filename = sys.argv[1]

f = open(filename, 'r')
src = f.readlines()
f.close()

for index,line in enumerate(src):         #replace tab characters with spaces so the parser doesn't choke on them
    src[index] = re.sub('\t','    ',line)

loadWordLists()

#parse the title - all the text up until the first .
#title is unimportant and is thrown out

while src[N].find('.') < 0:
    N += 1
N += 1
#title is thrown out

writeToFile("""
from __future__ import print_function
from Shakespeare import *
from getchar import getKey
from random import seed,randint

""")                           
                           
handleDeclarations()

writeToFile("""act=1

while 1:
    try:""")
parseAllActAndSceneDescriptions()

scenes = []
unfinished = False
while N < len(src):
    if beginsWithNoWhitespace(src[N], 'Act'):
        Assert (getActOrSceneNumber(src[N], 'Act') == actnum + 1, "Illegal Act numbering")
        if actnum > 0:
            writeScenes(scenes, False)
            scenes = []
        actnum += 1
        #act_names[getActOrSceneDescription(src[N])] = actnum
        N += 1
    elif beginsWithNoWhitespace(src[N], 'Scene'):
        Assert (getActOrSceneNumber(src[N], 'Scene') == len(scenes) + 1, "Illegal Scene numbering")
        #scene_names[getActOrSceneDescription(src[N])] = len(scenes) + 1
        N += 1
        speaker = ""
        target  = ""
        while (N < len(src)) and not (beginsWithNoWhitespace(src[N], 'Scene') or beginsWithNoWhitespace(src[N], 'Act')):
            if beginsWithNoWhitespace(src[N], '['):
                parseEnterOrExit()
                if not unfinished:
                    scenes.append("")
                    unfinished = True
                N += 1
            elif src[N].find(':') >= 0:
                name = ("".join((src[N][:src[N].find(':')]).split(" "))).lower()
                Assert (name in stage, "An actor who is not on stage is trying to speak")
                for actor in stage:
                    if actor != name:
                        target = actor
                        speaker = name
                if len(stage) == 1:
                    target = name   #what, people can't talk to themselves? :)
                    speaker = name
                N += 1
                statements = getStatements()
                scenecode = ""
                for statement in statements:
                    scenecode += parseStatement(statement)
                if not unfinished:
                    scenes.append(scenecode)
                    unfinished = True
                else:
                    scenes[-1] += scenecode
            else:
                N += 1
        unfinished = False

    else:
        N += 1
writeScenes(scenes, True)
writeToFile("    "*2+'break\n'+
"    except ActChange as e:\n"+
#"        print('Act Change: {}'.format(e))\n"+
"        continue\n")

sys.stdout.write(python_program)
#exec(python_program)
from collections import Counter
import re


class ConllEntry:
    def __init__(self, id, form, pos, cpos, parent_id=None, relation=None):
        self.id = id
        self.form = form
        self.norm = normalize(form)
        self.cpos = cpos.upper()
        self.pos = pos.upper()
        self.parent_id = parent_id
        self.relation = relation


class ParseForest:
    def __init__(self, sentence):
        self.roots = list(sentence)

        for root in self.roots:
            root.children = []
            root.scores = None
            root.parent = None
            root.pred_parent_id = 0 # None
            root.pred_relation = 'rroot' # None
            root.vecs = None
            root.lstms = None

    def __len__(self):
        return len(self.roots)


    def Attach(self, parent_index, child_index):
        parent = self.roots[parent_index]
        child = self.roots[child_index]

        child.pred_parent_id = parent.id
        del self.roots[child_index]


def isProj(sentence):
    forest = ParseForest(sentence)
    unassigned = {entry.id: sum([1 for pentry in sentence if pentry.parent_id == entry.id]) for entry in sentence}

    for _ in xrange(len(sentence)):
        for i in xrange(len(forest.roots) - 1):
            if forest.roots[i].parent_id == forest.roots[i+1].id and unassigned[forest.roots[i].id] == 0:
                unassigned[forest.roots[i+1].id]-=1
                forest.Attach(i+1, i)
                break
            if forest.roots[i+1].parent_id == forest.roots[i].id and unassigned[forest.roots[i+1].id] == 0:
                unassigned[forest.roots[i].id]-=1
                forest.Attach(i, i+1)
                break

    return len(forest.roots) == 1

def vocab(conll_path):
    wordsCount = Counter()
    posCount = Counter()
    relCount = Counter()

    with open(conll_path, 'r') as conllFP:
        for sentence in read_conll(conllFP, True):
            wordsCount.update([node.norm for node in sentence])
            posCount.update([node.pos for node in sentence])
            relCount.update([node.relation for node in sentence])

    return (wordsCount, {w: i for i, w in enumerate(wordsCount.keys())},  posCount.keys(), relCount.keys())

def read_conll(fh, proj):
    dropped = 0
    read = 0
    root = ConllEntry(0, '*root*', 'ROOT-POS', 'ROOT-CPOS', 0, 'rroot')
    tokens = [root]
    for line in fh:
        tok = line.strip().split()
        if not tok:
            if len(tokens)>1:
                if not proj or isProj(tokens):
                    yield tokens
                else:
                    print 'Non-projective sentence dropped'
                    dropped += 1
                read += 1
            tokens = [root]
            id = 0
        else:
            tokens.append(ConllEntry(int(tok[0]), tok[1], tok[3], tok[4], int(tok[6]) if tok[6] != '_' else -1, tok[7]))
    if len(tokens) > 1:
        yield tokens

    print dropped, 'dropped non-projective sentences.'
    print read, 'sentences read.'


def write_conll(fn, conll_gen):
    with open(fn, 'w') as fh:
        for sentence in conll_gen:
            for entry in sentence[1:]:
                fh.write('\t'.join([str(entry.id), entry.form, '_', entry.pos, entry.cpos, '_', str(entry.pred_parent_id), entry.pred_relation, '_', '_']))
                fh.write('\n')
            fh.write('\n')


numberRegex = re.compile("[0-9]+|[0-9]+\\.[0-9]+|[0-9]+[0-9,]+");
def normalize(word):
    return 'NUM' if numberRegex.match(word) else word.lower()

cposTable = {"PRP$": "PRON", "VBG": "VERB", "VBD": "VERB", "VBN": "VERB", ",": ".", "''": ".", "VBP": "VERB", "WDT": "DET", "JJ": "ADJ", "WP": "PRON", "VBZ": "VERB", 
             "DT": "DET", "#": ".", "RP": "PRT", "$": ".", "NN": "NOUN", ")": ".", "(": ".", "FW": "X", "POS": "PRT", ".": ".", "TO": "PRT", "PRP": "PRON", "RB": "ADV", 
             ":": ".", "NNS": "NOUN", "NNP": "NOUN", "``": ".", "WRB": "ADV", "CC": "CONJ", "LS": "X", "PDT": "DET", "RBS": "ADV", "RBR": "ADV", "CD": "NUM", "EX": "DET", 
             "IN": "ADP", "WP$": "PRON", "MD": "VERB", "NNPS": "NOUN", "JJS": "ADJ", "JJR": "ADJ", "SYM": "X", "VB": "VERB", "UH": "X", "ROOT-POS": "ROOT-CPOS", 
             "-LRB-": ".", "-RRB-": "."}


########################################################################################################################
# CONLL-U format:

# 0    ID: Word index, integer starting at 1 for each new sentence; may be a range for tokens with multiple words.
# 1    FORM: Word form or punctuation symbol.
# 2    LEMMA: Lemma or stem of word form.
# 3    UPOSTAG: Universal part-of-speech tag drawn from our revised version of the Google universal POS tags.
# 4    XPOSTAG: Language-specific part-of-speech tag; underscore if not available.
# 5    FEATS: List of morphological features from the universal feature inventory or from a defined language-specific extension; underscore if not available.
# 6    HEAD: Head of the current token, which is either a value of ID or zero (0).
# 7    DEPREL: Universal Stanford dependency relation to the HEAD (root iff HEAD = 0) or a defined language-specific subtype of one.
# 8    DEPS: List of secondary dependencies (head-deprel pairs).
# 9    MISC: Any other annotation.

def read_conll_u(filename):
    "Conllu parallel to read_conll; yields lists of ConllEntry objects."
    with open(filename) as f:
        root = ConllEntry(0, '*root*', 'ROOT-POS', 'ROOT-CPOS', 0, 'rroot')
        tokens = [root]
        for line in f:
            if line.startswith('#'):
                # This is just metadata.
                continue
            elif line == '\n':
                yield tokens
                tokens = [root]
            else:
                tok = line.strip().split()
                entry = ConllEntry(id = int(tok[0]),
                                   form = tok[1],
                                   pos = tok[3],
                                   cpos = '_',
                                   parent_id = int(tok[6]) if tok[6] != '_' else -1,
                                   relation = tok[7])
                tokens.append(entry)

def convert_conllu_to_conll(filename):
    "Convert a single file from conllu to conll."
    if filename.endswith('conllu'):
        write_conll(fn = filename[:-1],
                    conll_gen = read_conll_u(filename))
    else:
        raise ValueErrorError('This does not seem to be a .conllu file!')

def convert_all(dirname):
    "Convert all files in a particular directory from conllu to conll."
    files = glob.glob(dirname + '/*.conllu')
    print "Converting %d files" % len(files)
    for filename in files:
        convert_conllu_to_conll(filename)

###################################################################################################
# Scoring functionality to get the best epoch

def get_scores(filename):
    "Helper function to get scores from the evaluation file."
    lines = ['labeled_attachment', 'unlabeled_attachment', 'label_accuracy']
    with open(filename) as f:
        scores = [float(line.split('=')[1][1:-3]) 
                  for line, num in zip(f,range(3))]
        return dict(zip(lines, scores))

def file_score(filename, key='average'):
    "Helper function to return the score for a particular evaluation file."
    scores = get_scores(filename)
    if key == 'average':
        return sum(scores.values())/3
    elif key in ['labeled_attachment', 
                    'unlabeled_attachment', 
                    'label_accuracy']:
        return scores[key]
    else:
        return KeyError('Unknown key, cannot return score.')

def filename_to_num(filename):
    "Helper function that takes a filename and returns number in that filename."
    base_name = filename.split('.conll')[0]
    num = base_name.split('_')[-1]
    return int(num)

def select_first_file(filenames):
    "Helper function that returns the file with the lowest epoch number."
    return min((filename_to_num(fn),fn) for fn in filenames)

# Unlabeled attachment is used in recent papers, so let's go with that score.
def print_best_epoch(filenames, print_score=False, score_type='unlabeled_attachment'):
    """
    Prints the best epoch number. Import this function from parser.py.
    Filenames should be a list: ['dev_epoch_1.conll.txt', 'dev_epoch_2.conll.txt', ...]
    """
    scored = {filename: file_score(filename, score_type) for filename in filenames}
    max_value = max(scored.values())
    max_files = [filename for filename, score in scored.items() 
                          if score == max_value]
    best_epoch, filename = select_first_file(max_files)
    print "Best epoch:", best_epoch
    if print_score:
        print "Best score:", max_value

# vi: set ft=python sts=4 ts=4 sw=4 et:
#   For VI usage in the terminal

"""
A crossword puzzle generator.

Code borrowed and expanded from Sealhaung:
https://github.com/sealhuang/pycrossword
"""

import random
import re
import string
import time
from copy import copy as duplicate

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle


class Crossword(object):
    def __init__(self, cols, rows, empty='-', maxloops=2000, available_words=[]):
        self.cols = cols
        self.rows = rows
        self.empty = empty
        self.maxloops = maxloops
        self.available_words = available_words
        self.randomize_word_list()
        self.current_word_list = []
        self.clear_grid()
        self.debug = 0
 
    def clear_grid(self):
        """Initialize grid and fill with empty character."""
        self.grid = []
        for i in range(self.rows):
            ea_row = []
            for j in range(self.cols):
                ea_row.append(self.empty)
            self.grid.append(ea_row)
 
    def randomize_word_list(self):
        """Reset words and sort by length."""
        temp_list = []
        for word in self.available_words:
            if isinstance(word, Word):
                temp_list.append(Word(word.word, word.clue))
            else:
                temp_list.append(Word(word[0], word[1]))
        # randomize word list
        random.shuffle(temp_list)
        # sort by length
        temp_list.sort(key=lambda i: len(i.word), reverse=True)
        self.available_words = temp_list
 
    def compute_crossword(self, time_permitted=1.00, spins=2):
        copy = Crossword(self.cols, self.rows, self.empty,
                         self.maxloops, self.available_words)

        count = 0
        time_permitted = float(time_permitted)
        start_full = float(time.time())

        # only run for x seconds
        while (float(time.time()) - start_full) < time_permitted or count == 0:
            self.debug += 1
            copy.randomize_word_list()
            copy.current_word_list = []
            copy.clear_grid()

            x = 0
            # spins; 2 seems to be plenty
            while x < spins:
                for word in copy.available_words:
                    if word not in copy.current_word_list:
                        copy.fit_and_add(word)
                x += 1
            # buffer the best crossword by comparing placed words
            if len(copy.current_word_list) > len(self.current_word_list):
                self.current_word_list = copy.current_word_list
                self.grid = copy.grid
            count += 1
        return
 
    def suggest_coord(self, word):
        #count = 0
        coordlist = []
        glc = -1

        # cycle through letters in word
        for given_letter in word.word:
            glc += 1
            rowc = 0
            # cycle through rows
            for row in self.grid:
                rowc += 1
                colc = 0
                # cycle through letters in rows
                for cell in row:
                    colc += 1
                    # check match letter in word to letters in row
                    if given_letter == cell:
                        # suggest vertical placement 
                        try:
                            # make sure we're not suggesting a starting point off the grid
                            if rowc - glc > 0:
                                # make sure word doesn't go off of grid
                                if ((rowc - glc) + word.length) <= self.rows:
                                    coordlist.append([colc, rowc-glc, 1, colc+(rowc-glc),0])
                        except:
                            pass

                        # suggest horizontal placement 
                        try:
                            # make sure we're not suggesting a starting point off the grid
                            if colc - glc > 0: 
                                # make sure word doesn't go off of grid
                                if ((colc - glc) + word.length) <= self.cols:
                                    coordlist.append([colc-glc, rowc, 0, rowc+(colc-glc),0])
                        except:
                            pass

        # example: coordlist[0] = [col, row, vertical, col + row, score]
        new_coordlist = self.sort_coordlist(coordlist, word)
        #print(new_coordlist)

        return new_coordlist
 
    def sort_coordlist(self, coordlist, word):
        """Give each coordinate a score, then sort."""
        new_coordlist = []
        for coord in coordlist:
            col, row, vertical = coord[0], coord[1], coord[2]
            # checking scores
            coord[4] = self.check_fit_score(col, row, vertical, word)
            # 0 scores are filtered
            if coord[4]:
                new_coordlist.append(coord)
        # randomize coord list; why not?
        random.shuffle(new_coordlist)
        # put the best scores first
        new_coordlist.sort(key=lambda i: i[4], reverse=True)
        return new_coordlist
 
    def fit_and_add(self, word):
        """Doesn't really check fit except for the first word;
        otherwise just adds if score is good.
        """
        fit = False
        count = 0
        coordlist = self.suggest_coord(word)
 
        while not fit and count < self.maxloops:
            # this is the first word: the seed
            if len(self.current_word_list) == 0:
                # top left seed of longest word yields best results (maybe override)
                vertical, col, row = random.randrange(0, 2), 1, 1

                """ 
                # optional center seed method, slower and less keyword placement
                if vertical:
                    col = int(round((self.cols+1)/2, 0))
                    row = int(round((self.rows+1)/2, 0)) - int(round((word.length+1)/2, 0))
                else:
                    col = int(round((self.cols+1)/2, 0)) - int(round((word.length+1)/2, 0))
                    row = int(round((self.rows+1)/2, 0))
                # completely random seed method
                col = random.randrange(1, self.cols + 1)
                row = random.randrange(1, self.rows + 1)
                """
 
                if self.check_fit_score(col, row, vertical, word):
                    fit = True
                    self.set_word(col, row, vertical, word, force=True)

            # a subsquent words have scores calculated
            else:
                try:
                    col, row, vertical = coordlist[count][0], coordlist[count][1], coordlist[count][2]
                # no more cordinates, stop trying to fit
                except IndexError:
                    return
 
                # already filtered these out, but double check
                if coordlist[count][4]:
                    fit = True
                    self.set_word(col, row, vertical, word, force=True)
 
            count += 1

        return
 
    def check_fit_score(self, col, row, vertical, word):
        """Return score: 0 signifies no fit, 1 means a fit, 2+ means a cross.
        The more crosses the better.
        """
        if col < 1 or row < 1:
            return 0

        # give score a standard value of 1, will override with 0 if collisions detected
        count, score = 1, 1
        for letter in word.word:
            try:
                active_cell = self.get_cell(col, row)
            except IndexError:
                return 0
 
            if active_cell == self.empty or active_cell == letter:
                pass
            else:
                return 0
 
            if active_cell == letter:
                score += 1
 
            if vertical:
                # check surroundings
                if active_cell != letter: # don't check surroundings if cross point
                    if not self.check_if_cell_clear(col+1, row): # check right cell
                        return 0
 
                    if not self.check_if_cell_clear(col-1, row): # check left cell
                        return 0
 
                if count == 1: # check top cell only on first letter
                    if not self.check_if_cell_clear(col, row-1):
                        return 0
 
                if count == len(word.word): # check bottom cell only on last letter
                    if not self.check_if_cell_clear(col, row+1): 
                        return 0
            else: # else horizontal
                # check surroundings
                if active_cell != letter: # don't check surroundings if cross point
                    if not self.check_if_cell_clear(col, row-1): # check top cell
                        return 0
 
                    if not self.check_if_cell_clear(col, row+1): # check bottom cell
                        return 0
 
                if count == 1: # check left cell only on first letter
                    if not self.check_if_cell_clear(col-1, row):
                        return 0
 
                if count == len(word.word): # check right cell only on last letter
                    if not self.check_if_cell_clear(col+1, row):
                        return 0
 
            if vertical: # progress to next letter and position
                row += 1
            else: # else horizontal
                col += 1
 
            count += 1
 
        return score
 
    def set_word(self, col, row, vertical, word, force=False):
        """Set word in the grid, and adds word to word list."""
        if force:
            word.col = col
            word.row = row
            word.vertical = vertical
            self.current_word_list.append(word)
 
            for letter in word.word:
                self.set_cell(col, row, letter)
                if vertical:
                    row += 1
                else:
                    col += 1

        return
 
    def set_cell(self, col, row, value):
        self.grid[row-1][col-1] = value
 
    def get_cell(self, col, row):
        return self.grid[row-1][col-1]
 
    def check_if_cell_clear(self, col, row):
        try:
            cell = self.get_cell(col, row)
            if cell == self.empty: 
                return True
        except IndexError:
            pass
        return False
 
    def solution(self):
        """Return solution grid."""
        outStr = ""
        for r in range(self.rows):
            for c in self.grid[r]:
                outStr += '%s ' % c
            outStr += '\n'
        return outStr
 
    def word_find(self):
        """Return solution grid."""
        outStr = ""
        for r in range(self.rows):
            for c in self.grid[r]:
                if c == self.empty:
                    outStr += '%s ' % string.ascii_lowercase[random.randint(0,len(string.ascii_lowercase)-1)]
                else:
                    outStr += '%s ' % c
            outStr += '\n'
        return outStr
 
    def order_number_words(self):
        """Orders words and applies numbering system to them."""
        self.current_word_list.sort(key=lambda i: (i.col + i.row))
        count, icount = 1, 1
        for word in self.current_word_list:
            word.number = count
            if icount < len(self.current_word_list):
                if word.col == self.current_word_list[icount].col and word.row == self.current_word_list[icount].row:
                    pass
                else:
                    count += 1
            icount += 1
 
    def display(self, order=True):
        """Return (and order/number wordlist) the grid minus the words adding the numbers"""
        outStr = ""
        if order:
            self.order_number_words()
 
        copy = self
 
        for word in self.current_word_list:
            copy.set_cell(word.col, word.row, word.number)
 
        for r in range(copy.rows):
            for c in copy.grid[r]:
                outStr += '%s ' % c
            outStr += '\n'
 
        outStr = re.sub(r'[a-z]', ' ', outStr)
        return outStr
    
    def display_with_borders(self, order=True):
        """Return the grid with borders for cells containing letters, ensuring letters are hidden."""
        if order:
            self.order_number_words()

        # Create a new grid with letters replaced by hidden placeholders
        hidden_grid = []
        for row in self.grid:
            hidden_row = []
            for cell in row:
                if cell != self.empty and not cell.isdigit():  # Letter cells
                    hidden_row.append(" ")  # Hide the letter
                else:  # Empty or numbered cells
                    hidden_row.append(cell)
            hidden_grid.append(hidden_row)

        # Construct the bordered output
        output = []
        for row in hidden_grid:
            output_row = []
            for cell in row:
                if cell != self.empty:  # Add a border for non-empty cells
                    output_row.append("[ ]")
                else:  # No border for empty cells
                    output_row.append("   ")
            output.append(" ".join(output_row))

        return "\n".join(output)

    def word_bank(self):
        outStr = ''
        temp_list = duplicate(self.current_word_list)
        # randomize word list
        random.shuffle(temp_list)
        for word in temp_list:
            outStr += '%s\n' % word.word
        return outStr
 
    def legend(self):
        """Must order first.
        Splits the legend into horizontal and vertical clues."""
        horizontal_clues = []
        vertical_clues = []

        for word in self.current_word_list:
            clue = f'{word.number}. ({word.col},{word.row}) {word.down_across()}: {word.clue}'
            if word.vertical:
                vertical_clues.append(clue)
            else:
                horizontal_clues.append(clue)

        # Combine the horizontal clues first, followed by vertical ones
        outStr = "\n".join(horizontal_clues) + "\n\n" + "\n".join(vertical_clues)
        return outStr


class Word(object):
    def __init__(self, word=None, clue=None):
        self.word = re.sub(r'\s', '', word.lower())
        self.clue = clue
        self.length = len(self.word)
        # the below are set when placed on board
        self.row = None
        self.col = None
        self.vertical = None
        self.number = None
 
    def down_across(self):
        """Return down or across."""
        if self.vertical: 
            return 'down'
        else: 
            return 'across'
 
    def __repr__(self):
        return self.word
 

def load_word_list_from_txt(filename="words.txt"):
    word_list = []
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            # Strip leading/trailing whitespace
            line = line.strip()
            
            # Skip empty lines or lines that don't have the correct format
            if not line or "', '" not in line:
                continue
            
            # Split the line into word and definition
            word, definition = line.split("', '")
            word = word.strip("'")
            definition = definition.strip("'")
            word_list.append([word, definition])
    
    return word_list


def export_to_pdf(self, filename="crossword.pdf", title="Aaron and Ella"):
    """Export the crossword display and legend to a PDF."""
    # Prepare the document
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []

    # Add the title "Aaron and Ella" at the top
    styles = getSampleStyleSheet()
    title_style = styles['Title']  # Use 'Title' style from the stylesheet
    title_paragraph = Paragraph(title, title_style)
    elements.append(title_paragraph)

    # Generate the grid with numbers
    table_data = []
    for row in self.grid:
        table_row = []
        for cell in row:
            # Check if the cell is a number (int or str)
            if isinstance(cell, (int, str)) and str(cell).isdigit():
                table_row.append(str(cell))  # Add the number if it's a number (int or str)
            else:
                table_row.append("")  # Ensure letters are not printed
        table_data.append(table_row)

    # Create a table with cell styles
    table = Table(table_data, colWidths=[30] * self.cols, rowHeights=[30] * self.rows)  # Fixed width and height for uniform cells
    style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.15, colors.white),  # Borders for all cells
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),  # Background color
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center align text
    ])

    # Apply style for the cells containing the word numbers
    for word in self.current_word_list:
        for i in range(word.length):
            if word.vertical:
                col, row = word.col - 1, word.row - 1 + i
            else:
                col, row = word.col - 1 + i, word.row - 1
            style.add('BOX', (col, row), (col, row), 1, colors.black)  # Borders around the numbered cells

    table.setStyle(style)
    elements.append(table)

    # Add legend
    legend_data = [[self.legend()]]
    legend_table = Table(legend_data)
    elements.append(legend_table)

    # Build PDF
    doc.build(elements)
 
# word_list = [
#     ['saffron', 'The dried, orange yellow plant used to as dye and as a cooking spice.'],
#     ['pumpernickel', 'Dark, sour bread made from coarse ground rye.'],
#     ['leaven', 'An agent, such as yeast, that cause batter or dough to rise..'],
#     ['coda', 'Musical conclusion of a movement or composition.'],
#     ['paladin', 'A heroic champion or paragon of chivalry.'],
#     ['syncopation', 'Shifting the emphasis of a beat to the normally weak beat.'],
#     ['albatross', 'A large bird of the ocean having a hooked beek and long, narrow wings.'],
#     ['harp', 'Musical instrument with 46 or more open strings played by plucking.'],
#     ['piston', 'A solid cylinder or disk that fits snugly in a larger cylinder and moves under pressure as in an engine.'],
#     ['caramel', 'A smooth chery candy made from suger, butter, cream or milk with flavoring.'],
#     ['coral', 'A rock-like deposit of organism skeletons that make up reefs.'],
#     ['dawn', 'The time of each morning at which daylight begins.'],
#     ['pitch', 'A resin derived from the sap of various pine trees.'],
#     ['fjord', 'A long, narrow, deep inlet of the sea between steep slopes.'],
#     ['lip', 'Either of two fleshy folds surrounding the mouth.'],
#     ['lime', 'The egg-shaped citrus fruit having a green coloring and acidic juice.'],
#     ['mist','A mass of fine water droplets in the air near or in contact with the ground.'],
#     ['plague', 'A widespread affliction or calamity.'],
#     ['yarn', 'A strand of twisted threads or a long elaborate narrative.'],
#     ['snicker', 'A snide, slightly stifled laugh.'],
# ]
word_list = load_word_list_from_txt()
 
a = Crossword(20, 20, '-', 5000, word_list)
a.compute_crossword(2)
print(a.word_bank())
print(a.solution())
print(a.word_find())
print(a.display())
print(a.legend())
print(len(a.current_word_list), 'out of', len(word_list))
print(a.debug)

export_to_pdf(a, filename="crossword.pdf")

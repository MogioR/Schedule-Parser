from BukepParser import BukepParser
from BstuParser import BstuParser
from BelguParser import BelguParser
import time
parser = BukepParser()

#test = parser.getLecturersNames()

test0 = parser.getLecturersNames()
test = parser.getClasses()

for t in test0:
    print(t)

with open('lectors.txt', 'w') as f:
    for t in test0:
        f.write(str(t)+'\n')

with open('bukep_rasp.txt', 'w') as f:
    for t in test:
        f.write(str(t)+'\n')

print(len(test))
#print(test)
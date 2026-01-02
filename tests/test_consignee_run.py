from engine.extractors.odsfhiaclient1_format11_format1 import extract_consignee

sample = '''Name & Address of Recipient :                      Recipient PO No/Date :             Name & Address
VASU AGENCIES                                 1137432035/                           AKT MUTHU,
#26-B,
EAST JONES ROAD                               Recipient Code : 641052V008        padurPADUR
'''

print('INPUT:\n', sample)
res = extract_consignee(sample)
print('\nEXTRACTED:', res)

"""
Test the 118 fix logic
"""

plate = "TN118K7553"

print(f"Testing plate: {plate}")
print(f"Length: {len(plate)}")
print(f"plate[2:5] = '{plate[2:5]}'")
print(f"plate[5] = '{plate[5]}'")
print(f"plate[5].isalpha() = {plate[5].isalpha()}")

# Test the condition
if len(plate) >= 6:
    print("\n✓ Length check passed (>= 6)")
    
    if plate[2:5] == '118':
        print("✓ plate[2:5] == '118' passed")
    else:
        print(f"✗ plate[2:5] == '118' FAILED (got '{plate[2:5]}')")
    
    if len(plate) > 5:
        print("✓ len(plate) > 5 passed")
    else:
        print("✗ len(plate) > 5 FAILED")
    
    if plate[5].isalpha():
        print("✓ plate[5].isalpha() passed")
    else:
        print(f"✗ plate[5].isalpha() FAILED (plate[5] = '{plate[5]}')")
    
    # Full condition
    if (plate[2:5] == '118' and len(plate) > 5 and plate[5].isalpha()):
        print("\n🎉 ALL CONDITIONS MET - Fix should apply!")
        old_plate = plate
        plate = plate[0:2] + '18' + plate[5:]
        print(f"Result: {old_plate} → {plate}")
    else:
        print("\n❌ CONDITIONS NOT MET - Fix won't apply")
else:
    print("✗ Length check FAILED")

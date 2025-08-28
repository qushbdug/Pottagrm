#!/usr/bin/env python3
"""
Script to disable transfer fees across the bot
This will make all transfers FREE
"""

import re

def disable_fees_in_file(file_path):
    """Disable transfer fees in a specific file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Replace 1% fee calculation
        pattern1 = r'transfer_fee = amount \* 0\.01'
        replacement1 = 'transfer_fee = 0.0  # FREE transfers - no fees'
        content = re.sub(pattern1, replacement1, content)
        if pattern1 in original_content:
            changes_made.append("✅ Disabled 1% fee calculation")
        
        # Replace 10 riyal fixed fee
        pattern2 = r'fee = 10'
        replacement2 = 'fee = 0  # FREE transfers - no fees'
        content = re.sub(pattern2, replacement2, content)
        if 'fee = 10' in original_content:
            changes_made.append("✅ Disabled 10 riyal fixed fee")
        
        # Replace transfer fee text messages
        pattern3 = r'رسوم التحويل: 10 ريال'
        replacement3 = 'رسوم التحويل: مجاني 🆓'
        content = re.sub(pattern3, replacement3, content)
        if 'رسوم التحويل: 10 ريال' in original_content:
            changes_made.append("✅ Updated fee text: 10 riyal")
        
        # Replace 1% fee text
        pattern4 = r'سيتم خصم 1% رسوم تحويل'
        replacement4 = 'التحويل مجاني بدون رسوم 🆓'
        content = re.sub(pattern4, replacement4, content)
        if 'سيتم خصم 1% رسوم تحويل' in original_content:
            changes_made.append("✅ Updated fee text: 1%")
        
        # Replace fee description in confirmation text
        pattern5 = r'💳 رسوم التحويل \(1%\): \*\*\{transfer_fee:.2f\}\*\* ريال'
        replacement5 = '🆓 التحويل: **مجاني بدون رسوم**'
        content = re.sub(pattern5, replacement5, content)
        if '💳 رسوم التحويل (1%):' in original_content:
            changes_made.append("✅ Updated fee display in confirmation")
        
        # Replace fee description in summary
        pattern6 = r'💳 رسوم التحويل: \*\*\{transfer_fee:.2f\}\*\* ريال'
        replacement6 = '🆓 التحويل: **مجاني بدون رسوم**'
        content = re.sub(pattern6, replacement6, content)
        if '💳 رسوم التحويل: **' in original_content:
            changes_made.append("✅ Updated fee display in summary")
        
        # Replace total deduction calculation display
        pattern7 = r'📊 إجمالي الخصم: \*\*\{amount \+ transfer_fee:.2f\}\*\* ريال'
        replacement7 = '📊 إجمالي الخصم: **{amount:.2f}** ريال (بدون رسوم)'
        content = re.sub(pattern7, replacement7, content)
        if '📊 إجمالي الخصم: **{amount + transfer_fee' in original_content:
            changes_made.append("✅ Updated total deduction display")
        
        # Replace fee references in error messages
        pattern8 = r'💳 الرسوم: \{transfer_fee:.0f\} ريال'
        replacement8 = '🆓 الرسوم: مجاني'
        content = re.sub(pattern8, replacement8, content)
        if '💳 الرسوم: {transfer_fee' in original_content:
            changes_made.append("✅ Updated fee in error message")
        
        # Update balance calculations in confirmation text
        pattern9 = r'رصيدك بعد التحويل:\*\* \*\*\{user\[\'balance\'\] - total_deduction:.2f\}\*\* ريال'
        replacement9 = 'رصيدك بعد التحويل:** **{user[\'balance\'] - amount:.2f}** ريال'
        content = re.sub(pattern9, replacement9, content)
        
        # If any changes were made, write the file
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n📁 {file_path}:")
            for change in changes_made:
                print(f"  {change}")
            return True
        else:
            print(f"\n📁 {file_path}: No changes needed")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to disable fees in all files"""
    print("🚫 إيقاف رسوم التحويلات...")
    print("=" * 50)
    
    files_to_process = [
        'bot_modules/handlers.py',
        'yemen_net_bot_new.py'
    ]
    
    files_changed = 0
    
    for file_path in files_to_process:
        if disable_fees_in_file(file_path):
            files_changed += 1
    
    print(f"\n🎉 تم إيقاف الرسوم بنجاح!")
    print(f"📊 الملفات المحدثة: {files_changed}/{len(files_to_process)}")
    print("\n✅ جميع التحويلات أصبحت مجانية! 🆓")

if __name__ == "__main__":
    main()
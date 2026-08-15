import os
import sys
import datetime
import winreg as reg
import ctypes
import re

CYAN = "\033[96m"
RESET = "\033[0m"

# enable vtp for the current cmd session for ansi colors in win cmd
def enable_ansi_colors():
	try:
		kernel32 = ctypes.windll.kernel32
		handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
		mode = ctypes.c_uint()
		kernel32.GetConsoleMode(handle, ctypes.byref(mode))
		# ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
		kernel32.SetConsoleMode(handle, mode.value | 0x0004)
	except:
		pass  # we silently fail if not on windows or ansi is already enabled

# strip ansi codes from text b4 writing to logfiles
def strip_ansi(text):
	return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

# safely check if we are running with Administrator privileges
def is_admin():
	try:
		return ctypes.windll.shell32.IsUserAnAdmin() != 0
	except:
		return False

# setup logging
def get_log_file_path():
	script_dir = os.path.dirname(os.path.abspath(__file__))
	timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
	return os.path.join(script_dir, f"vmfake_log_{timestamp}.txt")

LOG_FILE = get_log_file_path()

# unified logging prints colors to console and writes plain text to logfile
def log_message(message, level="INFO", include_timestamp=True):
	ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
	file_line = f"[{ts}] {level}: {strip_ansi(message)}"
	
	if include_timestamp:
		console_line = f"[{ts}] {level}: {message}"
	else:
		console_line = message
	
	print(console_line)
	
	with open(LOG_FILE, "a", encoding="utf-8") as f:
		f.write(file_line + "\n")

# core registry functions
def create_key(path, name, value, type=reg.REG_SZ):
	# attempt to write a registry key. returns True on success, False on failure
	full_path = f"{path}\\{name}" if name else path
	try:
		key = reg.CreateKeyEx(reg.HKEY_LOCAL_MACHINE, path, 0, reg.KEY_SET_VALUE)
		reg.SetValueEx(key, name, 0, type, value)
		reg.CloseKey(key)
		log_message(f"Successfully created: {full_path}")
		return True
	except PermissionError:
		log_message(f"Permission error on {full_path} (run as Admin!)", "ERROR")
		return False
	except Exception as e:
		log_message(f"Error creating {full_path}: {e}", "ERROR")
		return False

def add_vm_keys():
	# add fake VM registry keys and track success/failure counts
	vm_registry_keys = [
		# VMware Keys
		(r"SYSTEM\CurrentControlSet\Services\Disk\Enum", "0", "VMware Virtual disk SCSI Disk Device", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Disk\Enum", "1", "VBOX HARDDISK", reg.REG_SZ),
		(r"HARDWARE\ACPI\DSDT\VMWARE__\00000001", None, b"\x00\x00\x00\x00", reg.REG_BINARY),
		(r"HARDWARE\ACPI\FADT\VMWARE__\00000001", None, b"\x00\x00\x00\x00", reg.REG_BINARY),
		(r"HARDWARE\ACPI\RSDT\VMWARE__\00000001", None, b"\x00\x00\x00\x00", reg.REG_BINARY),
		(r"SOFTWARE\VMware, Inc.\VMware Tools", "InstallPath", "C:\\Program Files\\VMware\\VMware Tools\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VMware Tools", "DisplayName", "VMware Tools", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VMware Tools", "ImagePath", "C:\\Program Files\\VMware\\VMware Tools\\VMToolsSvc.exe", reg.REG_SZ),

		# VirtualBox Keys
		(r"SOFTWARE\Oracle\VirtualBox Guest Additions", "InstallDir", "C:\\Program Files\\Oracle\\VirtualBox Guest Additions\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VBoxService", "DisplayName", "VBoxService", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VBoxService", "ImagePath", "C:\\Program Files\\Oracle\\VirtualBox Guest Additions\\VBoxService.exe", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VBoxGuest", "DisplayName", "VBoxGuest", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VBoxGuest", "ImagePath", "C:\\Program Files\\Oracle\\VirtualBox Guest Additions\\VBoxGuest.sys", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VBoxAdditions", "DisplayName", "VBoxAdditions", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VBoxAdditions", "ImagePath", "C:\\Program Files\\Oracle\\VirtualBox Guest Additions\\VBoxAdditions.sys", reg.REG_SZ),
		(r"HARDWARE\ACPI\DSDT\VBOX__\00000001", None, b"\x00\x00\x00\x00", reg.REG_BINARY),
		(r"HARDWARE\ACPI\FADT\VBOX__\00000001", None, b"\x00\x00\x00\x00", reg.REG_BINARY),
		(r"HARDWARE\ACPI\RSDT\VBOX__\00000001", None, b"\x00\x00\x00\x00", reg.REG_BINARY),

		# Parallels Keys
		(r"SOFTWARE\Parallels\Parallels Tools", "InstallPath", "C:\\Program Files\\Parallels\\Parallels Tools\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\prl_service", "DisplayName", "Parallels Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\prl_service", "ImagePath", "C:\\Program Files\\Parallels\\Parallels Tools\\prl_service.exe", reg.REG_SZ),
		(r"HARDWARE\ACPI\DSDT\PARALLEL__\00000001", None, b"\x00\x00\x00\x00", reg.REG_BINARY),
		(r"HARDWARE\ACPI\FADT\PARALLEL__\00000001", None, b"\x00\x00\x00\x00", reg.REG_BINARY),
		(r"HARDWARE\ACPI\RSDT\PARALLEL__\00000001", None, b"\x00\x00\x00\x00", reg.REG_BINARY),

		# Microsoft Virtual Machine Additions Keys
		(r"SOFTWARE\Microsoft\Virtual Machine Additions", "InstallPath", "C:\\Program Files\\Microsoft Virtual Machine Additions\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\vmadditions", "DisplayName", "Microsoft Virtual Machine Additions", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\vmadditions", "ImagePath", "C:\\Program Files\\Microsoft Virtual Machine Additions\\vmadditions.sys", reg.REG_SZ),

		# Microsoft Virtual Machine Guest Keys
		(r"SOFTWARE\Microsoft\Virtual Machine\Guest", "InstallPath", "C:\\Program Files\\Microsoft Virtual Machine Guest\\", reg.REG_SZ),

		# Hyper-V Keys
		(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Virtualization\Hyper-V", "InstallPath", "C:\\Program Files\\Hyper-V\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Hyper-V-Guest-Integration-Service", "DisplayName", "Hyper-V Guest Integration Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Hyper-V-Guest-Integration-Service", "ImagePath", "C:\\Windows\\System32\\vmmemctl.sys", reg.REG_SZ),

		# KVM Keys
		(r"SOFTWARE\KVM", "InstallDir", "C:\\Program Files\\KVM\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\kvm_service", "DisplayName", "KVM Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\kvm_service", "ImagePath", "C:\\Program Files\\KVM\\kvm_service.exe", reg.REG_SZ),

		# Citrix Keys
		(r"SOFTWARE\Citrix", "InstallDir", "C:\\Program Files\\Citrix\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\ctxsvc", "DisplayName", "Citrix Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\ctxsvc", "ImagePath", "C:\\Program Files\\Citrix\\ctxsvc.exe", reg.REG_SZ),

		# Cuckoo Sandbox Keys
		(r"SOFTWARE\Cuckoo Sandbox", "InstallDir", "C:\\Program Files\\Cuckoo Sandbox\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\CuckooSandbox", "DisplayName", "Cuckoo Sandbox Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\CuckooSandbox", "ImagePath", "C:\\Program Files\\Cuckoo Sandbox\\cuckoo_service.exe", reg.REG_SZ),

		# VirusTotal Keys
		(r"SOFTWARE\VirusTotal", "InstallPath", "C:\\Program Files\\VirusTotal\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VirusTotal", "DisplayName", "VirusTotal Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\VirusTotal", "ImagePath", "C:\\Program Files\\VirusTotal\\virustotal_service.exe", reg.REG_SZ),

		# Hybrid Analysis Keys
		(r"SOFTWARE\Hybrid Analysis", "InstallPath", "C:\\Program Files\\Hybrid Analysis\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\HybridAnalysis", "DisplayName", "Hybrid Analysis Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\HybridAnalysis", "ImagePath", "C:\\Program Files\\Hybrid Analysis\\hybrid_analysis_service.exe", reg.REG_SZ),

		# Wireshark Keys
		(r"SOFTWARE\Wireshark", "InstallDir", "C:\\Program Files\\Wireshark\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Wireshark", "DisplayName", "Wireshark", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Wireshark", "ImagePath", "C:\\Program Files\\Wireshark\\wireshark.exe", reg.REG_SZ),

		# Ghidra Keys
		(r"SOFTWARE\Ghidra", "InstallPath", "C:\\Program Files\\Ghidra\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Ghidra", "DisplayName", "Ghidra Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Ghidra", "ImagePath", "C:\\Program Files\\Ghidra\\ghidra_service.exe", reg.REG_SZ),

		# Intezer Keys
		(r"SOFTWARE\Intezer", "InstallDir", "C:\\Program Files\\Intezer\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Intezer", "DisplayName", "Intezer Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Intezer", "ImagePath", "C:\\Program Files\\Intezer\\intezer_service.exe", reg.REG_SZ),

		# REMnux Keys
		(r"SOFTWARE\REMnux", "InstallDir", "C:\\Program Files\\REMnux\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\REMnux", "DisplayName", "REMnux Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\REMnux", "ImagePath", "C:\\Program Files\\REMnux\\remnux_service.exe", reg.REG_SZ),

		# Joe Security GmbH Keys
		(r"SOFTWARE\JoeSecurity", "InstallDir", "C:\\Program Files\\Joe Security GmbH\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\JoeSecurity", "DisplayName", "Joe Security Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\JoeSecurity", "ImagePath", "C:\\Program Files\\Joe Security GmbH\\joesecurity_service.exe", reg.REG_SZ),

		# Radare2 Keys
		(r"SOFTWARE\Radare2", "InstallDir", "C:\\Program Files\\Radare2\\", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Radare2", "DisplayName", "Radare2 Service", reg.REG_SZ),
		(r"SYSTEM\CurrentControlSet\Services\Radare2", "ImagePath", "C:\\Program Files\\Radare2\\radare2_service.exe", reg.REG_SZ),
	]

	total = len(vm_registry_keys)
	successful = 0
	failed = 0

	log_message(f"Starting registry write. Total keys to process: {total}", "INFO")
	
	for path, name, value, *rest in vm_registry_keys:
		key_type = reg.REG_SZ
		if rest:
			key_type = rest[0]
		
		if create_key(path, name, value, key_type):
			successful += 1
		else:
			failed += 1
	
	return successful, failed

def menu():
	# admin-privileges check at startup
	log_message("", include_timestamp=False)
	log_message(f"{CYAN}VM Environment Emulator - Fake Registry Implant{RESET}", include_timestamp=False)
	log_message(f"Logfile will be saved to:", "INFO")
	log_message(f"{LOG_FILE}", "INFO")
	
	if is_admin():
		log_message(f"{CYAN}Script is running with Administrator privileges. Continue.{RESET}", include_timestamp=False)
	else:
		log_message(f"{CYAN}You are NOT running as Administrator. Abort.{RESET}", "ERROR")
		log_message(f"{CYAN}Registry writes will likely FAIL. Permission errors will be logged.{RESET}", include_timestamp=False)
		log_message("1. Continue anyway (expecting 100% failure rate)", include_timestamp=False)
		log_message("2. Exit and re-run as Administrator (recommended)", include_timestamp=False)
		
		log_message("", include_timestamp=False)
		choice = input("Enter your choice: ")
		log_message(f"User entered: {choice}")
		if choice == '1':
			log_message("User chose to continue WITHOUT Administrator privileges.", "WARNING")
			log_message("Continuing... (expect permission errors)", include_timestamp=False)
		elif choice == '2':
			log_message("User chose to exit due to missing Administrator privileges.")
			sys.exit()
		else:
			log_message("Invalid choice on admin warning. Exiting.", "ERROR")
			sys.exit()

	# main menu
	log_message("", include_timestamp=False)
	log_message("="*58, include_timestamp=False)
	log_message("This is a fork of Germanized's Fake-Vm found here:", include_timestamp=False)
	log_message("https://github.com/Germanized/Fake-Vm/", include_timestamp=False)
	log_message("="*58, include_timestamp=False)
	log_message("", include_timestamp=False)
	log_message("Choose an option:", include_timestamp=False)
	log_message("1. Add VM registry keys", include_timestamp=False)
	log_message("2. Exit", include_timestamp=False)
	
	log_message("", include_timestamp=False)
	choice = input("Enter your choice: ")
	log_message(f"User entered: {choice}")
	
	if choice == '1':
		successful, failed = add_vm_keys()
		
		# end summary
		log_message("", include_timestamp=False)
		log_message("="*58, include_timestamp=False)
		log_message(f"Process completed. Successful: {successful}, Failed: {failed}")
		log_message(f"{CYAN}Log file saved to: {LOG_FILE}{RESET}", include_timestamp=False)
		
		if failed == 0:
			log_message(f"{CYAN}All keys added successfully! System now mimics a VM environment.{RESET}", include_timestamp=False)
		else:
			log_message(f"{CYAN}Completed with {failed} errors. Check the log file above for details.{RESET}", include_timestamp=False)
		
		log_message("="*58, include_timestamp=False)
		
	elif choice == '2':
		log_message("User chose to exit.")
		sys.exit()
	else:
		log_message(f"{CYAN}Invalid choice. Please choose 1 or 2.{RESET}", include_timestamp=False)

if __name__ == "__main__":
	enable_ansi_colors()
	menu()

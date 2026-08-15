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
		pass

# strip ansi codes from text before writing to logfiles
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
	return os.path.join(script_dir, f"vmreverser_log_{timestamp}.txt")

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

# attempt to delete a registry key or value. returns True on success, False on failure
def delete_key(path, name):
	full_path = f"{path}\\{name}" if name else path
	try:
		key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, path, 0, reg.KEY_SET_VALUE)
		if name is None:
			reg.DeleteKey(key, "")
		else:
			reg.DeleteValue(key, name)
		reg.CloseKey(key)
		log_message(f"Successfully deleted: {full_path}")
		return True
	except FileNotFoundError:
		log_message(f"Not found (skipped): {full_path}", "WARNING")
		return True
	except PermissionError:
		log_message(f"Permission error on {full_path} (run as Admin!)", "ERROR")
		return False
	except Exception as e:
		log_message(f"Error deleting {full_path}: {e}", "ERROR")
		return False

def remove_vm_keys():
	# remove fake VM registry keys and track success/failure counts
	vm_registry_keys = [
		# VMware Keys
		(r"SYSTEM\CurrentControlSet\Services\Disk\Enum", "0"),
		(r"SYSTEM\CurrentControlSet\Services\Disk\Enum", "1"),
		(r"HARDWARE\ACPI\DSDT\VMWARE__\00000001", None),
		(r"HARDWARE\ACPI\FADT\VMWARE__\00000001", None),
		(r"HARDWARE\ACPI\RSDT\VMWARE__\00000001", None),
		(r"SOFTWARE\VMware, Inc.\VMware Tools", "InstallPath"),
		(r"SYSTEM\CurrentControlSet\Services\VMware Tools", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\VMware Tools", "ImagePath"),

		# VirtualBox Keys
		(r"SOFTWARE\Oracle\VirtualBox Guest Additions", "InstallDir"),
		(r"SYSTEM\CurrentControlSet\Services\VBoxService", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\VBoxService", "ImagePath"),
		(r"SYSTEM\CurrentControlSet\Services\VBoxGuest", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\VBoxGuest", "ImagePath"),
		(r"SYSTEM\CurrentControlSet\Services\VBoxAdditions", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\VBoxAdditions", "ImagePath"),
		(r"HARDWARE\ACPI\DSDT\VBOX__\00000001", None),
		(r"HARDWARE\ACPI\FADT\VBOX__\00000001", None),
		(r"HARDWARE\ACPI\RSDT\VBOX__\00000001", None),

		# Parallels Keys
		(r"SOFTWARE\Parallels\Parallels Tools", "InstallPath"),
		(r"SYSTEM\CurrentControlSet\Services\prl_service", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\prl_service", "ImagePath"),
		(r"HARDWARE\ACPI\DSDT\PARALLEL__\00000001", None),
		(r"HARDWARE\ACPI\FADT\PARALLEL__\00000001", None),
		(r"HARDWARE\ACPI\RSDT\PARALLEL__\00000001", None),

		# Microsoft Virtual Machine Additions Keys
		(r"SOFTWARE\Microsoft\Virtual Machine Additions", "InstallPath"),
		(r"SYSTEM\CurrentControlSet\Services\vmadditions", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\vmadditions", "ImagePath"),

		# Microsoft Virtual Machine Guest Keys
		(r"SOFTWARE\Microsoft\Virtual Machine\Guest", "InstallPath"),

		# Hyper-V Keys
		(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Virtualization\Hyper-V", "InstallPath"),
		(r"SYSTEM\CurrentControlSet\Services\Hyper-V-Guest-Integration-Service", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\Hyper-V-Guest-Integration-Service", "ImagePath"),

		# KVM Keys
		(r"SOFTWARE\KVM", "InstallDir"),
		(r"SYSTEM\CurrentControlSet\Services\kvm_service", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\kvm_service", "ImagePath"),

		# Citrix Keys
		(r"SOFTWARE\Citrix", "InstallDir"),
		(r"SYSTEM\CurrentControlSet\Services\ctxsvc", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\ctxsvc", "ImagePath"),

		# Cuckoo Sandbox Keys
		(r"SOFTWARE\Cuckoo Sandbox", "InstallDir"),
		(r"SYSTEM\CurrentControlSet\Services\CuckooSandbox", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\CuckooSandbox", "ImagePath"),

		# VirusTotal Keys
		(r"SOFTWARE\VirusTotal", "InstallPath"),
		(r"SYSTEM\CurrentControlSet\Services\VirusTotal", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\VirusTotal", "ImagePath"),

		# Hybrid Analysis Keys
		(r"SOFTWARE\Hybrid Analysis", "InstallPath"),
		(r"SYSTEM\CurrentControlSet\Services\HybridAnalysis", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\HybridAnalysis", "ImagePath"),

		# Wireshark Keys
		(r"SOFTWARE\Wireshark", "InstallDir"),
		(r"SYSTEM\CurrentControlSet\Services\Wireshark", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\Wireshark", "ImagePath"),

		# Ghidra Keys
		(r"SOFTWARE\Ghidra", "InstallPath"),
		(r"SYSTEM\CurrentControlSet\Services\Ghidra", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\Ghidra", "ImagePath"),

		# Intezer Keys
		(r"SOFTWARE\Intezer", "InstallDir"),
		(r"SYSTEM\CurrentControlSet\Services\Intezer", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\Intezer", "ImagePath"),

		# REMnux Keys
		(r"SOFTWARE\REMnux", "InstallDir"),
		(r"SYSTEM\CurrentControlSet\Services\REMnux", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\REMnux", "ImagePath"),

		# Joe Security GmbH Keys
		(r"SOFTWARE\JoeSecurity", "InstallDir"),
		(r"SYSTEM\CurrentControlSet\Services\JoeSecurity", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\JoeSecurity", "ImagePath"),

		# Radare2 Keys
		(r"SOFTWARE\Radare2", "InstallDir"),
		(r"SYSTEM\CurrentControlSet\Services\Radare2", "DisplayName"),
		(r"SYSTEM\CurrentControlSet\Services\Radare2", "ImagePath"),
	]

	total = len(vm_registry_keys)
	successful = 0
	failed = 0
	not_found = 0

	log_message(f"Starting registry cleanup. Total keys to process: {total}")

	for path, name in vm_registry_keys:
		result = delete_key(path, name)
		if result is True:
			successful += 1
		else:
			failed += 1

	return successful, failed

def menu():
	# admin-privileges check at startup
	log_message("", include_timestamp=False)
	log_message(f"{CYAN}VM Environment Reverser - Remove Fake Registry Implant{RESET}", include_timestamp=False)
	log_message(f"{CYAN}Logfile will be saved to: {LOG_FILE}{RESET}", include_timestamp=False)

	if is_admin():
		log_message(f"{CYAN}Script is running with Administrator privileges. Continue.{RESET}", include_timestamp=False)
	else:
		log_message(f"{CYAN}You are NOT running as Administrator. Abort.{RESET}", "ERROR")
		log_message(f"{CYAN}Registry deletions will likely FAIL. Permission errors will be logged.{RESET}", include_timestamp=False)
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
	log_message("1. Remove VM registry keys", include_timestamp=False)
	log_message("2. Exit", include_timestamp=False)

	log_message("", include_timestamp=False)
	choice = input("Enter your choice: ")
	log_message(f"User entered: {choice}")

	if choice == '1':
		successful, failed = remove_vm_keys()

		# end summary
		log_message("", include_timestamp=False)
		log_message("="*58, include_timestamp=False)
		log_message(f"Process completed. Successful: {successful}, Failed: {failed}")
		log_message(f"{CYAN}Log file saved to: {LOG_FILE}{RESET}", include_timestamp=False)

		if failed == 0:
			log_message(f"{CYAN}All keys removed successfully! VM fingerprints cleared.{RESET}", include_timestamp=False)
		else:
			log_message(f"{CYAN}Completed with {failed} errors. Check the log file for details.{RESET}", include_timestamp=False)

		log_message("="*58, include_timestamp=False)

	elif choice == '2':
		log_message("User chose to exit.")
		sys.exit()
	else:
		log_message(f"{CYAN}Invalid choice. Please choose 1 or 2.{RESET}", include_timestamp=False)

if __name__ == "__main__":
	enable_ansi_colors()
	menu()

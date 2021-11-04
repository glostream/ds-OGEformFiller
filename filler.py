from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import os
import re
import time


CSVPATH = 'data/NM_12_17_2020_noDups.csv'
URL = 'https://extapps2.oge.gov/201/Presiden.nsf/f54fd322068f23a385257fc40006f88e?OpenForm'


def getNames(path, oldIndex):
	names = []
	with open(path, 'r') as f:
		head = f.readline()
		heads = head.split(';')
		lastNameIndex = heads.index('pn_lastname')
		fullNameIndex = heads.index('pn_fullname')
		agencyIndex = heads.index('pn_agency')

		for i in range(oldIndex):
			f.readline()

		for index, line in enumerate(f):
			cols = line.split(';')
			lastName = cols[lastNameIndex]
			fullName = cols[fullNameIndex]
			agency = cols[agencyIndex]
			# print((lastName, fullName))
			names.append((lastName, fullName, agency))
			if len(names) == 25:
				return names, index + oldIndex + 1


def createLogFile():
	timeNow = time.strftime("%y%m%d%H", time.localtime())
	fileName = 'logs/log-{}.csv'.format(timeNow)
	with open(fileName, 'w+') as f:
		s = 'pn_fullname;pn_agency;notes;position;disclosures_requested\n'
		f.write(s)
	return fileName


def logRequest(path, fullName, agency, note='', position='', disclosures=''):
	# timeNow = time.strftime("%y%m%d%H", time.localtime())
	# fileName = 'logs/log-{}.csv'.format(timeNow)
	with open(path, 'a+') as f:
		if note:
			s = '{};{};{};;\n'.format(fullName, agency, note)
			f.write(s)
		# elif fullName:
		# 	f.write('\n{};{};;'.format(fullName, agency))
		elif disclosures:
			s = '{};{};;{};'.format(fullName, agency, position)
			f.write(s)
			for d in disclosures:
				if d == disclosures[-1]:
					f.write('{}'.format(d))
				else:
					f.write('{},'.format(d))
			f.write('\n')


def loadIndex():
	if os.path.isfile('data/index'):
		with open('data/index', 'r') as f:
			return int(f.read())
	else:
		return 0


def writeIndex(index):
	with open('data/index', 'w+') as f:
		f.write(str(index))


def main():
	index = loadIndex()
	names, newIndex = getNames(CSVPATH, index)
	writeIndex(newIndex)

	logFilePath = createLogFile()

	print(names[0], names[-1], newIndex, len(names))
	# return
	chromeOptions = webdriver.ChromeOptions()
	chromeOptions.add_argument('--headless')
	# chromeOptions.add_argument('--window-size=1920,1080')
	# chromeOptions.add_argument("--log-level=3")
	
	driver = webdriver.Chrome(executable_path='data/chromedriver', options=chromeOptions)
	driver.get(URL)

	actions = ActionChains(driver)

	# names = [('Azar', 'Alex Michael Azar II')]
	# names = [('Moore', 'Raymond H. Moore'), ('Connery', 'Joyce Michael Azar II')]

	# names = [('Aponte', 'Mari Carmen Aponte', 'Department of State')]
	for ln, fn, ag in names:
		print('\n', ln, fn)

		# requestedDisclosures = []
		positions = []

		lastNameField = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="LastName"]')))
		lastNameField.clear()
		lastNameField.send_keys(ln)

		mainWindow = driver.window_handles[0]

		findButton = driver.find_element_by_xpath('//*[@id="bodycontent"]/table/tbody/tr[2]/td/p[1]/input[1]').click()
		driver.switch_to.window(driver.window_handles[1])

		html = driver.page_source
		key = 'No filers with last name:'
		if re.search(key, html, re.IGNORECASE):
			print('Filer with last name {} not found'.format(ln))
			logRequest(logFilePath, fn, ag, 'No filer with last name "{}"'.format(ln))
			driver.close()
			driver.switch_to.window(mainWindow)
			continue

		else:
			filers = driver.find_elements_by_xpath('//*[@id="Filer"]')
			filerFound = False
			for f in filers:
				filerDetails = f.find_element_by_xpath('..').text
				# print(filerDetails)
				position = filerDetails.split(', ')[2]
				# print(position)
				if filerDetails.split(' ')[1] == fn.split(' ')[0]:
					filerFound = True
					if position.lower() not in map(lambda x : x.lower(), positions):
						positions.append(position)
					# f.click()
					# break
			if not filerFound:
				print('Filer with full name {} not found'.format(fn))
				logRequest(logFilePath, fn, ag, 'No filer with full name "{}"'.format(fn))
				driver.close()
				driver.switch_to.window(mainWindow)
				continue
				
			# filerDetails = driver.find_element_by_xpath('//*[@id="content"]/div[1]/label[1]').text
			# logRequest(logFilePath, fn, ag)

			for p in positions:
				requestedDisclosures = []

				# print('current position:', p)
				filers = driver.find_elements_by_xpath('//*[@id="Filer"]')
				for f in filers:
					filerDetails = f.find_element_by_xpath('..').text
					# print('details:', filerDetails)
					position = filerDetails.split(', ')[2]
					if filerDetails.split(' ')[1] == fn.split(' ')[0]:
						if position.lower() == p.lower():
							f.click()
							break
				
				disclosures = driver.find_elements_by_class_name('tooltip-input')
				if len(disclosures) == 0:
					logRequest(logFilePath, fn, ag, 'No disclosures found for full name "{}" and position "{}"'.format(fn, p))
					driver.close()
					driver.switch_to.window(mainWindow)

					if p == positions[-1]:
						break

					lastNameField = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="LastName"]')))
					lastNameField.clear()
					lastNameField.send_keys(ln)

					mainWindow = driver.window_handles[0]

					findButton = driver.find_element_by_xpath('//*[@id="bodycontent"]/table/tbody/tr[2]/td/p[1]/input[1]').click()
					driver.switch_to.window(driver.window_handles[1])
					continue

				# print(len(disclosures))
				for i in range(len(disclosures) // 5 + 1):
					# print(i)
					disclosures = driver.find_elements_by_class_name('tooltip-input')

					upperIndex = (i+1)*5
					if len(disclosures) < (i+1)*5:
						upperIndex = len(disclosures)
					for d in disclosures[i*5 : upperIndex]:
						d.click()
						text = d.find_element_by_xpath('..').text
						requestedDisclosures.append(text)

					addToCart = driver.find_element_by_xpath('//*[@id="content"]/div[2]/input').click()
					
					driver.switch_to.window(mainWindow)
					

					yourNameField = driver.find_element_by_xpath('//*[@id="Name"]')
					yourNameField.send_keys('David Szakonyi')
					# yourNameField.send_keys('Jason Barrella')

					addressField = driver.find_element_by_xpath('//*[@id="Address"]')
					addressField.send_keys('2115 G St. NW')
					# addressField.send_keys('145 Arum Road, Table View')

					cityField = driver.find_element_by_xpath('//*[@id="City"]')
					cityField.send_keys('Washington')
					# cityField.send_keys('Cape Town')

					stateDropdown = driver.find_element_by_xpath('//*[@id="State"]').click()
					actions.send_keys('di').perform()
					actions.send_keys(Keys.ENTER).perform()

					# countyField = driver.find_element_by_xpath('//*[@id="Country"]')
					# countyField.clear()
					# countyField.send_keys('South Africa')

					emailField = driver.find_element_by_xpath('//*[@id="Email"]')
					emailField.send_keys('declarationlinkage@gmail.com')
					# emailField.send_keys('jmbtis@gmail.com')

					occupationField = driver.find_element_by_xpath('//*[@id="Occupation"]')
					occupationField.send_keys('Professor')
					# occupationField.send_keys('Student')

					publicInterestGroupCheckbox = driver.find_element_by_xpath('/html/body/form/div[2]/table/tbody/tr[2]/td/p[2]/font[2]/label[3]/input').click()
					statementCheckbox = driver.find_element_by_xpath('//*[@id="CheckBoxAgree"]').click()

					## Submit ##
					submitButton = driver.find_element_by_xpath('//*[@id="bodycontent"]/table/tbody/tr[2]/td/p[3]/input').click()
					alert = driver.switch_to.alert
					alert.accept()

					nextFormButton = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/form/div[2]/div/a[1]/font'))).click()

					if upperIndex == len(disclosures):
						break

					lastNameField = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="LastName"]')))
					lastNameField.clear()
					lastNameField.send_keys(ln)

					mainWindow = driver.window_handles[0]

					findButton = driver.find_element_by_xpath('//*[@id="bodycontent"]/table/tbody/tr[2]/td/p[1]/input[1]').click()
					driver.switch_to.window(driver.window_handles[1])

					filers = driver.find_elements_by_xpath('//*[@id="Filer"]')
					for f in filers:
						filerDetails = f.find_element_by_xpath('..').text
						# print('details:', filerDetails)
						position = filerDetails.split(', ')[2]
						if filerDetails.split(' ')[1] == fn.split(' ')[0]:
							if position.lower() == p.lower():
								f.click()
								break
				
				logRequest(logFilePath, fn, ag, '', p, requestedDisclosures)

				if p == positions[-1]:
					break

				lastNameField = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="LastName"]')))
				lastNameField.clear()
				lastNameField.send_keys(ln)

				mainWindow = driver.window_handles[0]

				findButton = driver.find_element_by_xpath('//*[@id="bodycontent"]/table/tbody/tr[2]/td/p[1]/input[1]').click()
				driver.switch_to.window(driver.window_handles[1])


			# logRequest(logFilePath, fn, ag, '', p, requestedDisclosures)

	time.sleep(3)

	# driver.close()


if __name__ == '__main__':
	main()
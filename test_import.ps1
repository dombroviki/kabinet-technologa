$filePath = "D:\X\App\Подготовка_производства.xlsx"
$token = "QAR2nlYrAWHG2RMie94M5Qj-fP5M-7VaADwWX4E_HEE"
$fileBytes = [System.IO.File]::ReadAllBytes($filePath)
$fileContent = [System.Net.Http.ByteArrayContent]::new($fileBytes)
$form = [System.Net.Http.MultipartFormDataContent]::new()
$form.Add($fileContent, "file", "Подготовка_производства.xlsx")
$client = [System.Net.Http.HttpClient]::new()
$client.DefaultRequestHeaders.Add("X-Import-Token", $token)
$response = $client.PostAsync("http://127.0.0.1:5000/api/auto-import", $form).Result
$response.Content.ReadAsStringAsync().Result

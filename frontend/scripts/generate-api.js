import { generate } from 'openapi-typescript-codegen';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import axios from 'axios';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function generateApi() {
    const outputDir = path.resolve(__dirname, '../src/api/generated');
    const tempSchemaPath = path.resolve(__dirname, '../openapi.json');

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    try {
        console.log('⬇️  Fetching schema from http://localhost:8000/api/schema/?format=json ...');
        const response = await axios.get('http://localhost:8000/api/schema/?format=json');
        fs.writeFileSync(tempSchemaPath, JSON.stringify(response.data, null, 2));
        console.log('✅ Schema downloaded.');

        console.log('🔮 Generating API client...');
        await generate({
            input: tempSchemaPath,
            output: outputDir,
            clientName: 'ApiClient',
            useOptions: true,
            httpClient: 'axios',
        });
        console.log('✅ API Client generated successfully in src/api/generated');

        // Optional: Cleanup
        // fs.unlinkSync(tempSchemaPath);
    } catch (error) {
        console.error('❌ Error generating API client:', error.message || error);
        if (error.code === 'ECONNREFUSED') {
            console.error('👉 Make sure the Django Backend is running on port 8000');
        }
        process.exit(1);
    }
}

generateApi();

<?php

namespace Database\Seeders;

use App\Models\TranslatedText;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class TranslatedTextSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        TranslatedText::factory()->count(10)->create();
    }
}

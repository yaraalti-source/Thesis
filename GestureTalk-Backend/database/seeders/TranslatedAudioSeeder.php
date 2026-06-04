<?php

namespace Database\Seeders;

use App\Models\TranslatedAudio;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class TranslatedAudioSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        TranslatedAudio::factory()->count(10)->create();
    }
}

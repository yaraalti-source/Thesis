<?php

namespace Database\Factories;

use App\Models\Translation;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\TranslatedText>
 */
class TranslatedTextFactory extends Factory
{
    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'translation_id' => Translation::factory(), 
            'text' => $this->faker->sentence(), 
            'created_at' => now(),
            'updated_at' => now(),
        ];
    }
}

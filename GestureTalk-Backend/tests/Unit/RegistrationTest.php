<?php

namespace Tests\Unit;

use Tests\TestCase;
use App\Models\User;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Facades\DB;

class RegistrationTest extends TestCase
{
// This ensures the database is fresh for each test

    /** @test */
    public function it_registers_a_new_user_successfully()
    {
        // Mock the request data
        $requestData = [
            'name' => 'John Doe',
            'email' => 'johndoe@example.com',
            'password' => 'password',
            'user_type' => 'regular',
        ];

        // Perform the registration request
        $response = $this->postJson('/api/register', $requestData);

        // Assert that the user was successfully created in the database
        $this->assertDatabaseHas('users', [
            'email' => 'johndoe@example.com',
            'name' => 'John Doe',
            'user_type' => 'regular',
        ]);

        // Assert that a token is returned and the response is successful
        $response->assertStatus(200)
                 ->assertJsonStructure([
                     'status',
                     'message',
                     'user' => [
                         'name',
                         'email',
                         'user_type',
                     ],
                     'authorisation' => [
                         'token',
                         'type',
                     ]
                 ]);
    }

    /** @test */
    public function it_fails_if_email_is_missing()
    {
        // Missing email field
        $requestData = [
            'name' => 'John Doe',
            'password' => 'password',
            'user_type' => 'regular',
        ];

        $response = $this->postJson('/api/register', $requestData);

        // Assert validation fails
        $response->assertStatus(422)
                 ->assertJsonValidationErrors(['email']);
    }

    /** @test */
    public function it_fails_if_user_type_is_invalid()
    {
        // Invalid user_type
        $requestData = [
            'name' => 'John Doe',
            'email' => 'johndoe@example.com',
            'password' => 'password',
            'user_type' => 'invalid_user_type',
        ];

        $response = $this->postJson('/api/register', $requestData);

        // Assert validation fails
        $response->assertStatus(422)
                 ->assertJsonValidationErrors(['user_type']);
    }

    /** @test */
    public function it_hashes_the_password_correctly()
    {
        $requestData = [
            'name' => 'Jane Doe',
            'email' => 'janedoe@example.com',
            'password' => 'securepassword',
            'user_type' => 'regular',
        ];

        $this->postJson('/api/register', $requestData);

        // Assert that the password is hashed in the database
        $user = User::where('email', 'janedoe@example.com')->first();
        $this->assertTrue(Hash::check('securepassword', $user->password));
    }
}
